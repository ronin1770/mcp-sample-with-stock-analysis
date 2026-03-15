# Settiing up MCP Server

We need to install following software (prerequisites) in order to run our Python based MCP Server. Please note we are using GCP based Ubuntu 24.04 instance.

## Prerequisite Software Installation



### 1. Python 3.11+ 
We will use Python 3.11+ for quickly building MCP servers and agent workflows. It is comes as standard for Ubuntu 24.04. We can test using following the following command:

```
python3 
```

Expected output:

``` 
Python 3.12.3 (main, Mar  3 2026, 12:15:18) [GCC 13.3.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> 
```

### 2. Python Vritual Environemnt
Use following command to install it:

```
apt install -y python3.12-venv
```

Once installed, you can create and  activate it using the following commands:

```
python3 -m venv renv
```

Activate it:

```
source renv/bin/activate
```

### 3. Install necessary libraries for this development.

```
pip install mcp httpx reportlab python-dotenv
```

### 4. How to run the MCP Server
We can now start our MCP server. Let's use a screen to start our MCP Server there. Run following command:

```
screen (press enter)
```

You will be presented with informative text and hit Enter to continue.

- Ensure your are in the MCP Server folder

- Activate the virtual environment (browsing to screen will disconnect you from virtual environment)
```
source renv/bin/activate
```

- Start the MCP server using the following command:

```
python mcp_server.py
```

- Exit the Screen by simultaneously pressing: CTRL + A + D

## Testing MCP Server using MCP Inspector

MCP Inspector is a developer debugging and testing tool used with Model Context Protocol (MCP) servers. It allows you to inspect, test, and interact with tools exposed by an MCP server before integrating it with an AI agent or application.

It allows you to inspect, test, and interact with tools exposed by an MCP server before integrating it with an AI agent or application. It acts like Postman/Swagger UI but for MCP servers.


