# SQLcl and MCP Setup

This guide covers installing Oracle SQLcl (SQL Command Line) and configuring it for MCP (Model Context Protocol) access.
The Database Agent uses MCP to communicate with Oracle via SQLcl.

## What is MCP?

**Model Context Protocol (MCP)** is a standardized protocol for AI applications to interact
with external tools and data sources. In this project:

- SQLcl provides an MCP server (`sql -mcp`)
- The Database Agent connects and interacts with this server

## Prerequisites

- Oracle Cloud wallet downloaded (from [02-oracle-cloud-setup.md](02-oracle-cloud-setup.md))
- Java 11 or higher installed

### Verify Java Installation

```bash
java -version
```

If Java is not installed, [start here](https://www.oracle.com/java/) for download instructions.

## Step 1: Download SQLcl

1. Navigate to [Oracle SQLcl Downloads](https://www.oracle.com/database/sqldeveloper/technologies/sqlcl/download/)
2. Download the latest version (requires Oracle account)
3. Extract the ZIP file

## Step 2: Add SQLcl to PATH

Add the `bin` directory from the extracted SQLcl folder to your system PATH.

## Step 3: Verify SQLcl Installation

```bash
sql -version
```

Expected output:
```
SQLcl: Release 25.x ...
```

## Step 4: Create the Agent User Saved Connection

The Database Agent uses a saved connection called `oracle_agent`. This connection:
- Uses the least-privilege agent user (not ADMIN)
- Is saved securely in SQLcl's connection manager
- Can be reused without re-entering credentials

> **Important**: SQLcl MCP mode only works with pre-saved connections. The wallet must remain as a ZIP file.
> Previous extractions are allowed but the zip file must also be present for MCP configuration.

### Create the Saved Connection

1. Start SQLcl without connecting:
   ```bash
   sql /nolog
   ```

2. Load the cloud wallet:
   ```sql
   set cloudconfig /path/to/Wallet_<dbname>.zip
   ```

   Replace with your actual wallet path, e.g.:
   ```sql
   set cloudconfig /Users/me/wallet/Wallet_moviedb.zip
   ```

3. Connect and save credentials:
   ```sql
   conn -save oracle_agent -savepwd <username>/<password>@<tns_alias>
   ```

   Replace:
   - `<username>` with your `ORACLE_AGENT_USERNAME` (e.g., `movie_agent`)
   - `<password>` with your `ORACLE_AGENT_PASSWORD`
   - `<tns_alias>` with your TNS alias (e.g., `moviedb_low`)


   Example:
   ```sql
   conn -save oracle_agent -savepwd movie_agent/MyPass123@moviedb_low
   ```

4. Verify the saved connection:
   ```sql
   connmgr list
   ```

   You should see `oracle_agent` in the list.


5. Exit SQLcl:
   ```sql
   exit
   ```

## Step 5: Verify IDE/Terminal Environment

**Important**: If you're using an IDE like PyCharm or VS Code, it may not inherit your shell's PATH changes.
Restarting your IDE may be necessary to pick up recent changes.

## Troubleshooting

### "sql: command not found"
- SQLcl is not in your PATH
- Restart your terminal/IDE after modifying PATH

### "Connection 'oracle_agent' not found"
- The saved connection wasn't created
- Check with `connmgr list`

---

**Next**: [Jaeger Setup](05-jaeger-setup.md)
