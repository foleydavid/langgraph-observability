# Anthropic API Setup

This guide walks you through creating an Anthropic account and obtaining an API key for Claude.

## Step 1: Create an Anthropic Account

1. Navigate to [console.anthropic.com](https://console.anthropic.com/)
2. Click **Sign Up** (or **Get started**)
3. Create your account
4. Verify your email address

## Step 2: Set Up Billing

Anthropic requires a payment method to use the API.

1. In the Console, navigate to **Settings** > **Billing**
2. Click **Add payment method**
3. Enter your credit card details
4. Add credits or set up auto-recharge

### Cost Expectations

**Typical query cost**: $0.01 - $0.10 depending on:
- Query complexity (how many agents are called)
- Response length
- Number of tool calls

## Step 3: Generate an API Key

1. In the Console, navigate to **API Keys** (or **Settings** > **API Keys**)
2. Click **Create Key**
3. Give your key a name (e.g., `langgraph-observability`)
4. Click **Create**
5. **Copy the key immediately** (it won't be shown again)

The key will look like:
```
sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Step 4: Store Your API Key

Add the key to your project's `.env` file:

```
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

---

**Next**: [SQLcl & MCP Setup](04-sqlcl-mcp-setup.md)
