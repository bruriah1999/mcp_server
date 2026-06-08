from fastmcp import FastMCP

mcp = FastMCP("my-server")


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Return a greeting for the given name."""
    return f"Hello, {name}!"


@mcp.prompt()
def review_prompt(code: str) -> str:
    """Generate a code review prompt."""
    return f"Please review the following code:\n\n{code}"


if __name__ == "__main__":
    mcp.run()
