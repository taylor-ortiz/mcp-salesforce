from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
from simple_salesforce import Salesforce
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI client and credentials
client = OpenAI(api_key=os.getenv("OPEN_AI_KEY"))
key = os.getenv("SALESFORCE_KEY")
secret = os.getenv("SALESFORCE_SECRET")

# Initialize FastMCP server
mcp = FastMCP("salesforce")


def activate_sf_session():
    sf = Salesforce(
        username=os.getenv("SALESFORCE_USERNAME"),
        password=os.getenv("SALESFORCE_PASSWORD"),
        consumer_key=key,
        consumer_secret=secret
    )
    return sf


def filter_fields(object_description):
    """
    Given an object description (the result of sf_object.describe()),
    return a list of dictionaries for each field with selected attributes.
    """
    fields = object_description.get("fields", [])
    filtered_fields = []
    for field in fields:
        filtered_fields.append({
            "name": field.get("name"),
            "label": field.get("label"),
            "type": field.get("type"),
            "nillable": field.get("nillable"),
            "createable": field.get("createable"),
            "updateable": field.get("updateable"),
            "length": field.get("length"),
            "precision": field.get("precision"),
            "scale": field.get("scale"),
            "picklistValues": field.get("picklistValues", []),
            "externalId": field.get("externalId", False),
            "unique": field.get("unique", False),
            "referenceTo": field.get("referenceTo")
        })
    return filtered_fields


def describe_objects(sf_session):
    # Describe the entire org: returns info about all SObjects
    org_describe = sf_session.describe()
    sobjects = org_describe["sobjects"]
    user_friendly_objects = [
        obj for obj in sobjects
        if obj.get("queryable", False)
        and not obj.get("deprecatedAndHidden", False)
        and obj.get("layoutable", False)
    ]
    object_api_names = [obj["name"] for obj in user_friendly_objects]
    return object_api_names


def describe_object_fields(sf_session, object_name):
    try:
        sf_object = getattr(sf_session, object_name)
        object_description = sf_object.describe()
        if object_description:
            return filter_fields(object_description)
        return None
    except AttributeError:
        print(f"Error: Salesforce object '{object_name}' does not exist in this session.")


# Define the prompt for initial object identification.
@mcp.prompt()
def identify_salesforce_object_prompt(user_query: str, allowed_objects: str) -> str:
    return (
        f"You are a helpful bot that identifies Salesforce objects based on user queries.\n"
        f"You have the following Salesforce objects to choose from: {allowed_objects}.\n"
        f"Given the user query \"{user_query}\",\n"
        f"please return ONLY the name of the one Salesforce object that best matches this request.\n"
        f"Do not include any additional text or explanation."
    )


# Define a clarifying prompt if the initial object identification is ambiguous.
@mcp.prompt()
def clarifying_object_prompt(user_query: str, allowed_objects: str) -> str:
    return (
        f"The initial query \"{user_query}\" did not clearly indicate which Salesforce object to use.\n"
        f"Please clarify by selecting one of these objects: {allowed_objects}.\n"
        f"Return ONLY the object name and nothing else."
    )

@mcp.prompt()
def summarize_response_prompt(response: str) -> str:
    return (
        "You are a helpful assistant who summarizes Salesforce query results for end users.\n\n"
        "Below is the raw response from a Salesforce query:\n\n"
        f"{response}\n\n"
        "Please provide a clear and concise summary of the results. Your summary should include:\n"
        "- The total number of records returned (if available).\n"
        "- Key highlights from the data (e.g., important field values from the first record).\n"
        "Return only the summary text in plain language without any additional commentary or formatting."
    )


@mcp.prompt()
def generate_soql_with_describes_prompt(object_name: str, fields_metadata: str, user_query: str) -> str:
    return (
        f"You are a helpful bot that generates valid SOQL queries using Salesforce object metadata.\n\n"
        f"Below are some examples of how Simple Salesforce constructs queries:\n\n"
        f"1. Basic query:\n"
        f"   sf.query(\"SELECT Id, Email, ParentAccount.Name FROM Contact WHERE LastName = 'Jones'\")\n\n"
        f"2. Query all records:\n"
        f"   sf.query_all(\"SELECT Id, Email FROM Contact WHERE LastName = 'Jones'\")\n\n"
        f"3. Dynamic attribute insertion using format_soql:\n"
        f"   sf.query(format_soql(\"SELECT Id, Email FROM Contact WHERE LastName = {{}}\", \"Jones\"))\n"
        f"   sf.query(format_soql(\"SELECT Id, Email FROM Contact WHERE LastName = {{last_name}}\", last_name=\"Jones\"))\n"
        f"   sf.query(format_soql(\"SELECT Id, Email FROM Contact WHERE LastName IN {{names}}\", names=[\"Smith\", \"Jones\"]))\n\n"
        f"4. Using :literal to skip quoting/escaping for a value:\n"
        f"   sf.query(format_soql(\"SELECT Id, Email FROM Contact WHERE Income > {{:literal}}\", \"USD100\"))\n\n"
        f"5. Using :like to escape a substring for a LIKE expression:\n"
        f"   sf.query(format_soql(\"SELECT Id, Email FROM Contact WHERE Name LIKE '{{:like}}%'\", \"Jones\"))\n\n"
        f"6. SOSL search example:\n"
        f"   sf.search(\"FIND {{Jones}}\")\n\n"
        f"7. Quick Search (inserts the query inside the {{}} in the SOSL syntax):\n"
        f"   sf.quick_search(\"Jones\")\n\n"
        f"Now, given the following inputs:\n"
        f"- Salesforce object API name: {object_name}\n"
        f"- Field metadata for this object:\n{fields_metadata}\n"
        f"- User query: \"{user_query}\"\n\n"
        f"Your task is to generate a complete SOQL query that selects all fields from the {object_name} object and dynamically "
        f"incorporates filter conditions derived from the user query based on the metadata provided.\n\n"
        f"IMPORTANT:\n"
        f"- Examine the user query to determine if it is meant to return records specific to a user by looking for terms such as "
        f"'my', 'mine', 'owned by', or explicit names.\n"
        f"- If the query implies user-specific filtering (e.g. 'show me my cases' or 'John's cases'), do not output any "
        f"OwnerId filter if no literal user ID is provided. Instead, simply omit the OwnerId condition from the query.\n"
        f"  Do not output any placeholder such as 'USER_ID' or ':user_id'.\n"
        f"- If the query is general and not user-specific, do not include an OwnerId filter.\n\n"
        f"Return ONLY the raw SOQL query as plain text without any formatting, code fences, or markdown."
    )


def call_llm(prompt: str) -> str:
    response = client.responses.create(
        model="gpt-4o",
        input=prompt
    )
    if response:
        return response.output[0].content[0].text.strip()
    return None


# MCP tool that drives the query process.
@mcp.tool()
def query(user_query: str) -> str:
    sf_session = activate_sf_session()
    if sf_session:
        objects = describe_objects(sf_session)
        if objects:
            # Generate the initial prompt for object identification.
            prompt = identify_salesforce_object_prompt(user_query, str(objects))
            object_name = call_llm(prompt)
            print("Initial object identification:", object_name)
            
            # If the returned object isn't valid, ask a clarifying question.
            if object_name not in objects:
                clarifying = clarifying_object_prompt(user_query, str(objects))
                object_name = call_llm(clarifying)
                print("Clarified object identification:", object_name)
            
            # If we have a valid object, generate the SOQL query.
            if object_name in objects:
                fields = describe_object_fields(sf_session, object_name)
                soql_prompt = generate_soql_with_describes_prompt(object_name, str(fields), user_query)
                soql = call_llm(soql_prompt)
                print("Generated SOQL Query:", soql)
                if soql:
                    try:
                        result = sf_session.query(soql)
                        if result:
                            summary_prompt = summarize_response_prompt(result)
                            return call_llm(summary_prompt)
                    except AttributeError:
                        print("error processing the query")
                else:
                    return "No SOQL query generated."
            else:
                return "Unable to determine a valid Salesforce object from the query."
    return "No Salesforce session or objects found."


if __name__ == "__main__":
    print("Starting the Salesforce MCP server...")
    # Uncomment the next line to run the MCP server:
    mcp.run(transport="stdio")
    
    # For testing purposes, we call the query tool directly:
    # query('show me all of my cases that are still open')
    # summary = query('show me all of my opportunities where the amount is less than 500')
    # print(summary)
