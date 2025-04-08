https://github.com/user-attachments/assets/7e610150-b62e-4336-aa97-e241416e0567

# Salesforce MCP Query Generator

This project implements a multi-turn conversation system using **Fast MCP (Model Context Protocol)**, **Simple Salesforce**, and an LLM (via the OpenAI API). Its goal is to dynamically generate valid SOQL queries based on user input and Salesforce object metadata. In addition, the system can ask clarifying questions when the input is ambiguous and summarize query results for user-friendly output.

## Overview

The system performs the following tasks:
- **Salesforce Connection:** Establishes a connection to Salesforce using Simple Salesforce.
- **Metadata Retrieval:** Retrieves object-level and field-level metadata from Salesforce.
- **LLM Integration:** Uses prompt functions (decorated with `@mcp.prompt()`) to instruct an LLM (e.g., GPT-4 or Claude) to:
  - Identify which Salesforce object the user is querying (with clarifying prompts if needed).
  - Generate a complete SOQL query that selects all fields from the given object and dynamically incorporates filter conditions based on the user’s natural language query.
- **Query Execution:** Executes the generated SOQL query on Salesforce and (optionally) summarizes the results for the user.

## Features

- **Dynamic Query Generation:**  
  The system uses detailed field metadata to help the LLM generate accurate SOQL queries that respect field types, formatting conventions (including use of `format_soql`, `:literal`, and `:like`), and necessary filters.
  
- **Multi-Turn Conversation:**  
  If the initial query is ambiguous—such as when determining whether to filter by user-specific criteria—the LLM can ask clarifying questions. The multi-turn design ensures that the final query is as accurate as possible.

- **Response Summarization:**  
  The system can also generate a plain language summary of the query results to present the data in a user-friendly format.

## Setup

### Requirements

- **Python 3.8+** (using a virtual environment is recommended)
- **Fast MCP** – for constructing the multi-turn conversation and prompt tools
- **Simple Salesforce** – for connecting to and querying Salesforce
- **OpenAI Python Library** – for integration with your LLM (or your preferred LLM client)

### Installation

1. **Clone the Repository**

   ```bash
   git clone <repository_url>
   cd <repository_directory>

2. **Create and Activate a Virtual Environment (Optional)**

   ```python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # For Windows: venv\Scripts\activate

3. **Install Dependencies**
    pip install fastmcp simple-salesforce openai

4. **Configure Credentials**

    - Update your Salesforce credentials (username, password, consumer key, consumer secret) in your code.

    - Replace the OpenAI API key with your actual key.

    - Alternatively, use environment variables to provide these credentials securely.

### Running the MCP Server

For testing, you can call the MCP tool directly in your script. For multi-turn conversation mode, uncomment the MCP server run line in your code. For example:

    ```python
    if __name__ == "__main__":
        # Uncomment the next line to run the MCP server:
        # mcp.run(transport="stdio")
        
        # For testing purposes, we call the query tool directly:
        query('show me all of my cases that are still open')
    ```
## Code Structure

### Salesforce Connection & Metadata
- **`activate_sf_session()`**: Connects to Salesforce.
- **`describe_objects(sf_session)`**: Retrieves a list of queryable Salesforce object API names.
- **`filter_fields(object_description)`**: Filters field metadata, returning a list of dictionaries with selected attributes (e.g., `name`, `type`, `label`, etc.).
- **`describe_object_fields(sf_session, object_name)`**: Obtains field metadata for a specified object.

### LLM Prompt Functions (using Fast MCP)
- **`identify_salesforce_object_prompt(user_query, allowed_objects)`**: Creates a prompt to let the LLM decide which object is being queried.
- **`generate_soql_with_describes_prompt(object_name, fields_metadata, user_query)`**: Constructs a prompt that instructs the LLM to generate a complete SOQL query. This prompt includes examples of how to use the Simple Salesforce formatting functions such as `format_soql`, `:literal`, and `:like`.
- **`clarifying_object_prompt(user_query, allowed_objects)` (optional)**: Used to ask clarifying questions if the initial object identification is ambiguous.
- **`summarize_response_prompt(response)` (optional)**: Summarizes the Salesforce query results in plain language.

### MCP Tool – Query
- **`query(user_query)`**: This MCP tool ties together the Salesforce connection, metadata retrieval, LLM prompt calls, and query execution.
  - It contains logic for multi-turn clarification if the object identification is ambiguous (i.e., if no valid object is determined from the user's query, it asks for clarification).

## Example Usage

When a user inputs:

> "Show me all of my cases that are still open"

The system flow is as follows:

### 1. Object Identification
- The LLM uses the `identify_salesforce_object_prompt` to determine that the relevant Salesforce object is `Case`.  
- If the output is ambiguous (e.g., not in the allowed list), a clarifying prompt (`clarifying_object_prompt`) is issued to ask the user for more details.

### 2. Field Metadata Retrieval
- The system retrieves the metadata for the `Case` object.  
- It filters out irrelevant fields and retains only those useful for querying.

### 3. SOQL Query Generation
- The LLM uses `generate_soql_with_describes_prompt` to generate a complete SOQL query based on:
  - The Salesforce object name (`Case`),
  - The filtered field metadata, and
  - The original user query.
- **Special Handling for User-Specific Filtering:**  
  If the query implies user-specific filtering (e.g., "my cases") but no literal user ID is supplied, the prompt instructs the LLM to either omit the `OwnerId` filter or ask for clarification.

### 4. Query Execution & Summarization
- The generated SOQL query is executed using Simple Salesforce's `sf.query()` function.
- Optionally, a separate prompt (`summarize_response_prompt`) can summarize the query results in plain language for end-user display.

## Customization

### Modify Prompts
- You can tailor the text in the prompt functions to suit your domain-specific requirements or handle additional edge cases.

### Extend Functionality
- Additional MCP tools can be created for other tasks, such as record updating or deletion.

### Implement Multi-Turn Clarification
- Expand the multi-turn conversation flow to handle ambiguous user queries by asking follow-up questions. This ensures the final query is as accurate as possible.

## Updating Your `claude_desktop_config.json`

In order for Claude Desktop (or your MCP client) to properly launch and manage your MCP servers, you must update your `claude_desktop_config.json` configuration file with the correct paths for each server in your environment.

Below is an example configuration file with obfuscated paths. Replace the placeholder paths with the absolute paths on your system where the MCP server files reside:

```json
{
  "mcpServers": {
    "weather": {
      "command": "/path/to/uv",
      "args": [
        "--directory",
        "/absolute/path/to/parent/folder/weather",
        "run",
        "weather.py"
      ]
    },
    "salesforce": {
      "command": "/path/to/uv",
      "args": [
        "--directory",
        "/absolute/path/to/parent/folder/salesforce",
        "run",
        "mcp_salesforce.py"
      ]
    }
  }
}