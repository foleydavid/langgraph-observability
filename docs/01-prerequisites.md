# Prerequisites

Before starting the setup, ensure you have the following installed and accounts created.

## System Requirements

### Python 3.9+

This project requires Python 3.9 or later.

**Install Python:** [python.org/downloads](https://www.python.org/downloads/)

### Docker Desktop

Docker is required for running Jaeger (the trace visualization tool).

**Install Docker Desktop:**
- Download from [docker.com](https://www.docker.com/products/docker-desktop/)
- Follow the installation wizard
- Start Docker Desktop and ensure it's running

## Required Accounts

### Oracle Cloud Account (Free Tier)

You'll need an Oracle Cloud account to create an Autonomous Database. The **Always Free** tier will be fine.

**Sign up at**: [cloud.oracle.com](https://cloud.oracle.com/)

> **Note**: Oracle requires a credit card for verification but won't charge you for Free Tier resources.

See [02-oracle-cloud-setup.md](02-oracle-cloud-setup.md) for detailed setup instructions.

### Anthropic Account

You'll need an Anthropic API key to use Claude as the LLM.

**Sign up at**: [console.anthropic.com](https://console.anthropic.com/)

> **Note**: Anthropic requires payment setup. API usage is pay-per-use.
> Running this demo costs approximately $0.01-0.10 per query depending on response length.

See [03-anthropic-api-setup.md](03-anthropic-api-setup.md) for detailed setup instructions.

## Clone the Repository

Clone this project to your local machine:

```bash
git clone https://github.com/foleydavid/langgraph-observability.git
cd langgraph-observability
```

## Summary Checklist

- [ ] Python 3.9+ installed
- [ ] Docker Desktop installed and running
- [ ] Oracle Cloud account created
- [ ] Anthropic account created
- [ ] Repository cloned

---

**Next**: [Oracle Cloud Setup](02-oracle-cloud-setup.md)
