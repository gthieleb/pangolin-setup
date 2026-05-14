#!/usr/bin/env python3
"""
Pangolin OpenAPI MCP Proxy
Konvertiert die Pangolin Integration API in einen MCP Server
"""

import asyncio
import json
import os
import sys
from typing import Any

import yaml
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import httpx

# Konfiguration
OPENAPI_SPEC_PATH = "/opt/pangolin/config/openapi.yaml"
BASE_URL = "http://pangolin:3003"
API_KEY = os.environ.get("PANGOLIN_API_KEY", "")

class PangolinMCPProxy:
    def __init__(self):
        self.server = Server("pangolin-mcp")
        self.tools = []
        self.openapi_spec = None
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)
        
        if API_KEY:
            self.client.headers["Authorization"] = f"Bearer {API_KEY}"
        
        self._load_openapi_spec()
        self._setup_handlers()
    
    def _load_openapi_spec(self):
        """Lädt die OpenAPI Spec und extrahiert Tools"""
        with open(OPENAPI_SPEC_PATH, 'r') as f:
            self.openapi_spec = yaml.safe_load(f)
        
        # Konvertiere OpenAPI Paths zu MCP Tools
        for path, methods in self.openapi_spec.get('paths', {}).items():
            for method, details in methods.items():
                if method in ['get', 'post', 'put', 'delete', 'patch']:
                    tool_name = f"{method.upper()}_{path.replace('/', '_').replace('{', '').replace('}', '')}"
                    tool = Tool(
                        name=tool_name,
                        description=details.get('description', f'{method.upper()} {path}'),
                        inputSchema=self._extract_schema(details)
                    )
                    self.tools.append((tool, method, path))
    
    def _extract_schema(self, details: dict) -> dict:
        """Extrahiert Input Schema aus OpenAPI Operation"""
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        # Path Parameter
        for param in details.get('parameters', []):
            param_name = param['name']
            param_schema = param.get('schema', {'type': 'string'})
            schema['properties'][param_name] = param_schema
            if param.get('required'):
                schema['required'].append(param_name)
        
        # Request Body
        if 'requestBody' in details:
            content = details['requestBody'].get('content', {})
            if 'application/json' in content:
                body_schema = content['application/json'].get('schema', {})
                if 'properties' in body_schema:
                    for prop_name, prop_schema in body_schema['properties'].items():
                        schema['properties'][prop_name] = prop_schema
                if 'required' in body_schema:
                    schema['required'].extend(body_schema['required'])
        
        return schema
    
    def _setup_handlers(self):
        """Setup MCP Request Handler"""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [tool for tool, _, _ in self.tools]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            # Finde das passende Tool
            for tool, method, path in self.tools:
                if tool.name == name:
                    return await self._execute_request(method, path, arguments)
            
            return [TextContent(type="text", text=f"Tool {name} not found")]
    
    async def _execute_request(self, method: str, path: str, arguments: dict) -> list[TextContent]:
        """Führt HTTP Request aus"""
        try:
            # Ersetze Path Parameter
            for key, value in arguments.items():
                path = path.replace(f"{{{key}}}", str(value))
            
            # Separatoren für Query und Body
            query_params = {}
            body_params = {}
            
            for key, value in arguments.items():
                if f"{{{key}}}" not in path:  # Nicht ein Path Parameter
                    if method in ['GET', 'DELETE']:
                        query_params[key] = value
                    else:
                        body_params[key] = value
            
            # HTTP Request
            if method == 'GET':
                response = await self.client.get(path, params=query_params)
            elif method == 'POST':
                response = await self.client.post(path, json=body_params)
            elif method == 'PUT':
                response = await self.client.put(path, json=body_params)
            elif method == 'DELETE':
                response = await self.client.delete(path, params=query_params)
            elif method == 'PATCH':
                response = await self.client.patch(path, json=body_params)
            else:
                return [TextContent(type="text", text=f"Unsupported method: {method}")]
            
            result = {
                "status": response.status_code,
                "data": response.json() if response.content else None
            }
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def run(self):
        """Startet den MCP Server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )

if __name__ == "__main__":
    proxy = PangolinMCPProxy()
    asyncio.run(proxy.run())
