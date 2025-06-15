# File Classify Tool

## Overview
The `file_classify` tool uses AI-powered image classification to find and select the most relevant files from the available files in the current context based on a search query.

## How it works
1. User provides a natural language command like "find images of people" or "show me pictures of cars"
2. The system extracts the search query from the command
3. All available files in the current directory are classified using AI image recognition
4. The tool returns the top 3 most relevant files ranked by similarity score

## Parameters
- `query` (string): The search query describing what to look for in the files

## Example Usage
- "find images of people" → query: "people"
- "show me pictures of cars" → query: "cars"
- "get landscape photos" → query: "landscape"
- "search for animal images" → query: "animals"

## Response Format
```json
{
  "success": true,
  "tool_name": "file_classify",
  "params": {
    "query": "people",
    "results": [
      {
        "fileName": "portrait.jpg",
        "class": "person",
        "score": 95.5
      },
      {
        "fileName": "group_photo.png", 
        "class": "people",
        "score": 87.2
      }
    ],
    "directory": "/path/to/files"
  },
  "message": "Found 2 files matching 'people'."
}
```

## Integration Points
- Uses `FunRequest` from `cv_api.py` with `file_paths` and `query_string`
- Calls `api_image_classify` function for AI classification
- Utilizes fuzzy matching with thefuzz library for query-to-class matching
- Returns top 3 results sorted by relevance score

## Error Handling
- Validates that files are available in context
- Validates that current directory is provided
- Handles API errors gracefully
- Returns appropriate error messages for missing parameters
