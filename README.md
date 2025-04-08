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
