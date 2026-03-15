# This is the read me file for setting up REST API 

REST API component is developed using the *RUST*. This REST API communicates with 3rd party to retrieve Stock market quotes for the given symbols. This API is deployed on a **GCP VM running Ubuntu 24.04**. The following instructions are developed keeping this fact in mind.

## Pre-requisites Installation


### 1. SSH into your server using the following code:

```
ssh USER@SERVER_IP
```

### 2. Update the System

```
sudo apt update
sudo apt upgrade -y
```

### 3. Install essential utilities:

```
sudo apt install -y build-essential curl git pkg-config libssl-dev
```

### 4. Install Rust

Rust should not be installed via apt for production builds. Use rustup.

```
curl https://sh.rustup.rs -sSf | sh
```

Choose:

```
1) Proceed with installation
```

Then load environment:

```
source $HOME/.cargo/env
```

Verify:

```
rustc --version
cargo --version
```

### 5. Install Rust Toolchain Components

Recommended components for building APIs:

```
rustup update
rustup component add rustfmt clippy
```

### 6. Install System Dependencies for HTTP + TLS

API uses reqwest (HTTPS requests), so install SSL libraries.

```
sudo apt install -y libssl-dev ca-certificates
```

### 7. Clone the Git project

Clone from git; 

git clone https://github.com/ronin1770/mcp-sample-with-stock-analysis.git


### 8. Add Rust library for .env handling

Your code needs the AlphaVantage API key.

Install dotenv helper (optional):

```
cargo add dotenvy
```

### 9. Rename .sample.env to .env

Rename the .sample.env to .env

Set environment variable, ALPHAVANTAGE_API_KEY=<API_KEY>