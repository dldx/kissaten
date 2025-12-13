# HTTP Proxy Configuration

The Kissaten scraper supports HTTP and HTTPS proxy configuration for both `httpx` (HTTP requests) and `playwright` (browser automation).

## Configuration

Proxy settings are configured through environment variables in a `.env` file.

### Setup

1. Copy `env.example` to `.env`:
   ```bash
   cp env.example .env
   ```

2. Add proxy configuration to your `.env` file:
   ```bash
   # For HTTP and HTTPS traffic through the same proxy
   HTTP_PROXY=http://proxy.example.com:8080
   HTTPS_PROXY=http://proxy.example.com:8080

   # Or just HTTPS proxy (recommended)
   HTTPS_PROXY=https://proxy.example.com:8443
   ```

3. If your proxy requires authentication:
   ```bash
   HTTP_PROXY=http://username:password@proxy.example.com:8080
   HTTPS_PROXY=http://username:password@proxy.example.com:8080
   ```

### Proxy Priority

- If both `HTTP_PROXY` and `HTTPS_PROXY` are set, the scraper will prefer `HTTPS_PROXY`
- Both `httpx` (for HTTP requests) and `playwright` (for browser automation) will use the same proxy configuration

## Usage

Once configured in your `.env` file, all scrapers will automatically use the proxy:

```python
from kissaten.scrapers import get_scraper

# Scraper will automatically load proxy settings from .env
async with get_scraper("cartwheel_coffee") as scraper:
    beans = await scraper.scrape()
```

## Testing

To test if your proxy configuration works:

```bash
# Run proxy configuration tests
uv run pytest tests/test_proxy_configuration.py -v
```

## Supported Proxy Types

- **HTTP Proxy**: `http://proxy-server:port`
- **HTTPS Proxy**: `https://proxy-server:port`
- **SOCKS Proxy**: Not currently supported (httpx/playwright limitation)

## Troubleshooting

### Proxy not being used

1. Ensure your `.env` file is in the project root directory
2. Check that the proxy URL format is correct
3. Verify the proxy server is accessible from your network
4. Check logs for "Configured HTTP client with proxy" or "Configured Playwright browser with proxy" messages

### Authentication errors

If using proxy authentication:
- Ensure username and password are URL-encoded if they contain special characters
- Example: `http://user%40name:p%40ssword@proxy.example.com:8080`

### Connection timeouts

- Increase the timeout setting in scraper configuration
- Check if the proxy server allows connections to the target websites
- Verify firewall rules allow outbound connections through the proxy

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `HTTP_PROXY` | HTTP proxy server URL | `http://proxy.example.com:8080` |
| `HTTPS_PROXY` | HTTPS proxy server URL (preferred) | `https://proxy.example.com:8443` |

## Implementation Details

- Proxy configuration is loaded once during `BaseScraper.__init__()`
- Uses `python-dotenv` to load environment variables from `.env` file
- `httpx.AsyncClient` is configured with the `proxy` parameter
- `playwright` browser is launched with `proxy` option in launch options
- Proxy settings apply to all HTTP requests and browser automation for that scraper instance

## Security Considerations

- **Never commit `.env` files to version control**
- Store proxy credentials securely
- Use HTTPS proxies when possible for encrypted connections
- Rotate proxy credentials regularly if using authentication
