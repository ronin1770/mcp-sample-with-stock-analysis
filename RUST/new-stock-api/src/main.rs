use axum::{
    extract::{Query, State},
    Json,
};
use std::{collections::HashMap, sync::Arc};

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
            message: "Provide at least one symbol, e.g. ?symbols=MSFT,AAPL,NVDA"
                .to_string(),
        });
    }

    let mut quotes = Vec::new();

    for symbol in &symbols {
        let quote = fetch_quote(&state.http_client, &state.alpha_key, symbol).await?;
        quotes.push(quote);
    }

    Ok(Json(QuotesResponse {
        requested_symbols: symbols,
        quotes,
    }))
}

async fn fetch_quote(
    client: &Client,
    api_key: &str,
    symbol: &str,
) -> Result<QuoteDto, ApiError> {
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

    let q = parsed.global_quote;

    let price = q.price.parse::<f64>().map_err(|_| ApiError {
        status: StatusCode::BAD_GATEWAY,
        message: format!("Could not parse price for {}", symbol),
    })?;

    let previous_close = q.previous_close.parse::<f64>().map_err(|_| ApiError {
        status: StatusCode::BAD_GATEWAY,
        message: format!("Could not parse previous close for {}", symbol),
    })?;

    let change = q.change.parse::<f64>().map_err(|_| ApiError {
        status: StatusCode::BAD_GATEWAY,
        message: format!("Could not parse change for {}", symbol),
    })?;

    Ok(QuoteDto {
        symbol: q.symbol,
        price,
        previous_close,
        change,
        change_percent: q.change_percent,
        latest_trading_day: q.latest_trading_day,
    })
}