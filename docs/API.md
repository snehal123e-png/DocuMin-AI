# DocuMind AI REST API

Base URL: `http://127.0.0.1:8000`

Interactive Swagger UI: `/docs` · ReDoc: `/redoc`

## POST `/documents/upload`
Multipart form upload. Field name: `files` (one or more PDF files).
Returns processed page/chunk counts and current index statistics.

## GET `/documents`
Returns document count, page count, passage count and filenames.

## POST `/ask`
```json
{"question":"Summarize the paper's proposed method","top_k":4,"model":"llama3.2"}
```
Returns `answer` and a `sources` array. Each source includes `file`, `page`, `text`, and retrieval `score`.

## POST `/summary`
```json
{"filename":null,"length":"Standard","model":"llama3.2"}
```
`filename` may be a document filename or `null` for all documents. Length: `Brief`, `Standard`, or `Detailed`.

## POST `/flashcards`
```json
{"filename":null,"count":8,"model":"llama3.2"}
```
Returns an array of `question` / `answer` objects.
