use axum::{
    extract::{Query, State},
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::get,
    Json, Router,
};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::{collections::HashMap, env, io, net::SocketAddr, sync::Arc};
use tokio::net::TcpListener;
use tower_http::{cors::CorsLayer, trace::TraceLayer};
use tracing::info;
use tracing_subscriber::EnvFilter;

#[derive(Clone)]
struct AppState {
    http_client: Client,
    alpha_key: String,
}

#[derive(Debug, Deserialize)]
struct QuotesQuery {
    symbols: String,
}

#[derive(Debug, Serialize)]
struct QuotesResponse {
    requested_symbols: Vec<String>,
    quotes: Vec<QuoteDto>,
}

#[derive(Debug, Serialize)]
struct QuoteDto {
    symbol: String,
    price: f64,
    previous_close: f64,
    change: f64,
    change_percent: String,
    latest_trading_day: String,
}

#[derive(Debug, Deserialize)]
struct AlphaQuoteResponse {
    #[serde(rename = "Global Quote")]
    global_quote: Option<AlphaGlobalQuote>,
    #[serde(rename = "Note")]
    note: Option<String>,
    #[serde(rename = "Error Message")]
    error_message: Option<String>,
}

#[derive(Debug, Deserialize)]
struct AlphaGlobalQuote {
    #[serde(rename = "01. symbol")]
    symbol: Option<String>,
    #[serde(rename = "05. price")]
    price: Option<String>,
    #[serde(rename = "08. previous close")]
    previous_close: Option<String>,
    #[serde(rename = "09. change")]
    change: Option<String>,
    #[serde(rename = "10. change percent")]
    change_percent: Option<String>,
    #[serde(rename = "07. latest trading day")]
    latest_trading_day: Option<String>,
}

#[derive(Debug)]
struct ApiError {
    status: StatusCode,
    message: String,
}

#[derive(Serialize)]
struct ErrorBody {
    error: String,
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        (self.status, Json(ErrorBody { error: self.message })).into_response()
    }
}

#[derive(Serialize)]
struct HealthResponse {
    status: &'static str,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    dotenvy::dotenv().ok();

    let env_filter =
        EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info,tower_http=info"));
    tracing_subscriber::fmt().with_env_filter(env_filter).init();

    let alpha_key = env::var("ALPHAVANTAGE_API_KEY").map_err(|_| {
        io::Error::new(
            io::ErrorKind::InvalidInput,
            "Missing ALPHAVANTAGE_API_KEY in environment",
        )
    })?;

    let bind_address = env::var("BIND_ADDRESS").unwrap_or_else(|_| "0.0.0.0:8080".to_string());
    let addr: SocketAddr = bind_address.parse().map_err(|e| {
        io::Error::new(
            io::ErrorKind::InvalidInput,
            format!("Invalid BIND_ADDRESS '{}': {}", bind_address, e),
        )
    })?;

    let state = Arc::new(AppState {
        http_client: Client::new(),
        alpha_key,
    });

    let app = Router::new()
        .route("/health", get(health))
        .route("/quotes", get(get_quotes))
        .with_state(state)
        .layer(CorsLayer::permissive())
        .layer(TraceLayer::new_for_http());

    let listener = TcpListener::bind(addr).await?;
    info!("stock-api listening on {}", addr);
    axum::serve(listener, app).await?;
    Ok(())
}

async fn health() -> Json<HealthResponse> {
    Json(HealthResponse { status: "ok" })
}

async fn get_quotes(
    State(state): State<Arc<AppState>>,
    Query(params): Query<QuotesQuery>,
) -> Result<Json<QuotesResponse>, ApiError> {
    let symbols: Vec<String> = params
        .symbols
        .split(',')
        .map(|s| s.trim().to_uppercase())
        .filter(|s| !s.is_empty())
        .collect();

    if symbols.is_empty() {
        return Err(ApiError {
            status: StatusCode::BAD_REQUEST,
            message: "Provide at least one symbol, e.g. ?symbols=MSFT,AAPL,NVDA".to_string(),
        });
    }

    let mut quotes = Vec::with_capacity(symbols.len());
    for symbol in &symbols {
        let quote = fetch_quote(&state.http_client, &state.alpha_key, symbol).await?;
        quotes.push(quote);
    }

    Ok(Json(QuotesResponse {
        requested_symbols: symbols,
        quotes,
    }))
}

async fn fetch_quote(client: &Client, api_key: &str, symbol: &str) -> Result<QuoteDto, ApiError> {
    let mut query = HashMap::new();
    query.insert("function", "GLOBAL_QUOTE");
    query.insert("symbol", symbol);
    query.insert("apikey", api_key);

    let response = client
        .get("https://www.alphavantage.co/query")
        .query(&query)
        .send()
        .await
        .map_err(|e| ApiError {
            status: StatusCode::BAD_GATEWAY,
            message: format!("Failed to call Alpha Vantage: {}", e),
        })?;

    if !response.status().is_success() {
        return Err(ApiError {
            status: StatusCode::BAD_GATEWAY,
            message: format!("Alpha Vantage returned status {}", response.status()),
        });
    }

    let parsed: AlphaQuoteResponse = response.json().await.map_err(|e| ApiError {
        status: StatusCode::BAD_GATEWAY,
        message: format!("Invalid Alpha Vantage JSON response: {}", e),
    })?;

    if let Some(msg) = parsed.error_message.or(parsed.note) {
        return Err(ApiError {
            status: StatusCode::BAD_GATEWAY,
            message: format!("Alpha Vantage error for {}: {}", symbol, msg),
        });
    }

    let q = parsed.global_quote.ok_or_else(|| ApiError {
        status: StatusCode::BAD_GATEWAY,
        message: format!("No quote returned for {}", symbol),
    })?;

    let response_symbol = required_text(q.symbol, "01. symbol", symbol)?;
    let price = parse_f64(q.price, "05. price", symbol)?;
    let previous_close = parse_f64(q.previous_close, "08. previous close", symbol)?;
    let change = parse_f64(q.change, "09. change", symbol)?;
    let change_percent = required_text(q.change_percent, "10. change percent", symbol)?;
    let latest_trading_day = required_text(q.latest_trading_day, "07. latest trading day", symbol)?;

    Ok(QuoteDto {
        symbol: response_symbol,
        price,
        previous_close,
        change,
        change_percent,
        latest_trading_day,
    })
}

fn required_text(value: Option<String>, field: &str, symbol: &str) -> Result<String, ApiError> {
    value
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .ok_or_else(|| ApiError {
            status: StatusCode::BAD_GATEWAY,
            message: format!("Missing {} for {}", field, symbol),
        })
}

fn parse_f64(value: Option<String>, field: &str, symbol: &str) -> Result<f64, ApiError> {
    let raw = required_text(value, field, symbol)?;
    raw.parse::<f64>().map_err(|_| ApiError {
        status: StatusCode::BAD_GATEWAY,
        message: format!("Could not parse {}='{}' for {}", field, raw, symbol),
    })
}
