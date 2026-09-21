# HTTP Proxy Configuration

The Kissaten scrapers support HTTP and HTTPS proxy configuration for both `httpx` (HTTP requests) and `playwright` (browser automation).

Proxy settings are deliberately **scraper-scoped**: the `SCRAPER_*` variable names are not read by any other library in the process, so logfire, geocoding, and other services reach the internet directly instead of being routed through the scraper's egress proxy. Generic `HTTP_PROXY`/`HTTPS_PROXY` names are inherited by every HTTP library in the process — that misconfiguration took down logfire exports during the 2026-09-20/21 proxy outage and is why the scraper-specific names exist.

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
   SCRAPER_HTTP_PROXY=http://proxy.example.com:8080
   SCRAPER_HTTPS_PROXY=http://proxy.example.com:8080

   # Or just HTTPS proxy (recommended)
   SCRAPER_HTTPS_PROXY=https://proxy.example.com:8443
   ```

3. If your proxy requires authentication:
   ```bash
   SCRAPER_HTTP_PROXY=http://username:password@proxy.example.com:8080
   SCRAPER_HTTPS_PROXY=http://username:password@proxy.example.com:8080
   ```

### Proxy Priority

- If both `SCRAPER_HTTP_PROXY` and `SCRAPER_HTTPS_PROXY` are set, the scraper will prefer `SCRAPER_HTTPS_PROXY`
- Legacy `HTTP_PROXY`/`HTTPS_PROXY` are still honoured as a deprecated fallback when no `SCRAPER_*` variable is set (a deprecation warning is logged once per process); rename them in `.env` so other libraries stop inheriting the proxy
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
| `SCRAPER_HTTP_PROXY` | HTTP proxy server URL (scraper egress only) | `http://proxy.example.com:8080` |
| `SCRAPER_HTTPS_PROXY` | HTTPS proxy server URL (preferred, scraper egress only) | `https://proxy.example.com:8443` |
| `HTTP_PROXY` | Deprecated fallback for `SCRAPER_HTTP_PROXY` | `http://proxy.example.com:8080` |
| `HTTPS_PROXY` | Deprecated fallback for `SCRAPER_HTTPS_PROXY` | `https://proxy.example.com:8443` |

## Implementation Details

- Proxy configuration is loaded once during `BaseScraper.__init__()`
- Uses `python-dotenv` to load environment variables from `.env` file
- `SCRAPER_HTTP_PROXY` / `SCRAPER_HTTPS_PROXY` are read first, with legacy `HTTP_PROXY` / `HTTPS_PROXY` as fallback
- `httpx.AsyncClient` is configured with the `proxy` parameter
- `playwright` browser is launched with `proxy` option in launch options
- Proxy settings apply to all HTTP requests and browser automation for that scraper instance
- Other libraries in the same process are unaffected — do not set generic `HTTP_PROXY`/`HTTPS_PROXY` in `.env` unless you intend every HTTP client (logfire included) to use the proxy

## Security Considerations

- **Never commit `.env` files to version control**
- Store proxy credentials securely
- Use HTTPS proxies when possible for encrypted connections
- Rotate proxy credentials regularly if using authentication