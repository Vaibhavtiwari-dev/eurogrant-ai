# EuroGrant AI - API Documentation

This document describes the API endpoints available in the EuroGrant AI backend.

- **Base URL:** `http://localhost:8000`
- **API Prefix:** `/api/v1`
- **Interactive Documentation (Swagger):** `http://localhost:8000/docs`
- **Alternative Documentation (Redoc):** `http://localhost:8000/redoc`

---

## Table of Contents
1. [Authentication](#1-authentication)
2. [Users](#2-users)
3. [Organizations](#3-organizations)
4. [Uploads](#4-uploads)

---

## 1. Authentication

### Register
* **Endpoint:** `POST /api/v1/auth/register`
* **Description:** Register a new user and create an organization (if it doesn't exist).
* **Request Body (JSON):**
  ```json
  {
    "email": "user@example.com",
    "password": "securepassword",
    "full_name": "John Doe",
    "organization_name": "My Company",
    "invite_code": "MASTER_INVITE_CODE_HERE"
  }
  ```
* **Response (JSON - `201 Created`):**
  ```json
  {
    "id": 1,
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "ADMIN",
    "organization_id": 1,
    "created_at": "2026-05-25T12:00:00Z"
  }
  ```

### Login
* **Endpoint:** `POST /api/v1/auth/login`
* **Description:** Authenticate a user and set an `access_token` cookie.
* **Request Body (`application/x-www-form-urlencoded`):**
  * `username`: (email string)
  * `password`: (password string)
* **Response (JSON - `200 OK`):**
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer"
  }
  ```
* **Cookie Set:**
  * `access_token`: JWT token (`httpOnly`, `samesite=lax`, `secure` on production).

### Logout
* **Endpoint:** `POST /api/v1/auth/logout`
* **Description:** Clears the `access_token` cookie.
* **Response (JSON - `200 OK`):**
  ```json
  {
    "message": "Successfully logged out"
  }
  ```

---

## 2. Users

### Get Profile
* **Endpoint:** `GET /api/v1/users/me`
* **Description:** Get information about the currently logged-in user.
* **Headers Required:** 
  * `Authorization: Bearer <access_token>` (or via `access_token` Cookie)
* **Response (JSON - `200 OK`):**
  ```json
  {
    "id": 1,
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "ADMIN",
    "organization_id": 1,
    "created_at": "2026-05-25T12:00:00Z"
  }
  ```

---

## 3. Organizations

### Get My Organization
* **Endpoint:** `GET /api/v1/organizations/me`
* **Description:** Fetch the organization associated with the logged-in user.
* **Headers Required:**
  * `Authorization: Bearer <access_token>` (or via `access_token` Cookie)
* **Response (JSON - `200 OK`):**
  ```json
  {
    "id": 1,
    "name": "My Company",
    "created_at": "2026-05-25T12:00:00Z"
  }
  ```

### Get Dashboard Overview
* **Endpoint:** `GET /api/v1/organizations/dashboard-overview`
* **Description:** Retrieves high-fidelity metrics and lists of active pipelines & hot matches.
* **Headers Required:**
  * `Authorization: Bearer <access_token>` (or via `access_token` Cookie)
* **Response (JSON - `200 OK`):**
  ```json
  {
    "stats": {
      "active_high_matches": 1,
      "ai_generation_quality": 94,
      "total_pipeline_value": 1.5
    },
    "pipelines": [
      {
        "id": "EIC-2024-ACCELERATOR-01",
        "title": "Project GreenLithium • €2.5M Request",
        "status": "GENERATING",
        "progress": 65,
        "subtext": "Context Assembling (RAG)"
      }
    ],
    "hot_matches": [
      {
        "title": "Innovate UK: Smart Sustainable Manufacturing",
        "desc": "Direct alignment with your recent portfolio updates regarding IoT...",
        "score": 98,
        "time": "2H AGO"
      }
    ]
  }
  ```

---

## 4. Uploads

### List Company Documents
* **Endpoint:** `GET /api/v1/uploads/documents`
* **Description:** Retrieve a list of all uploaded company documents.
* **Headers Required:**
  * `Authorization: Bearer <access_token>` (or via `access_token` Cookie)
* **Response (JSON - `200 OK`):**
  ```json
  [
    {
      "id": "403cf24c-bf6f-45a8-9d62-9e20db9ceebc",
      "organization_id": 1,
      "file_name": "company_profile.pdf",
      "s3_key": "org_1/403cf24c-bf6f-45a8-9d62-9e20db9ceebc.pdf",
      "content_type": "application/pdf",
      "status": "PENDING",
      "created_at": "2026-05-25T12:00:00Z"
    }
  ]
  ```

### Upload Company Document
* **Endpoint:** `POST /api/v1/uploads/company-document`
* **Description:** Upload a PDF or DOCX file (up to 25MB). Requires **ADMIN** or **WRITER** role.
* **Headers Required:**
  * `Authorization: Bearer <access_token>` (or via `access_token` Cookie)
* **Request Body (`multipart/form-data`):**
  * `file`: File object (PDF or DOCX only)
* **Response (JSON - `201 Created`):**
  ```json
  {
    "id": "403cf24c-bf6f-45a8-9d62-9e20db9ceebc",
    "organization_id": 1,
    "file_name": "company_profile.pdf",
    "s3_key": "org_1/403cf24c-bf6f-45a8-9d62-9e20db9ceebc.pdf",
    "content_type": "application/pdf",
    "status": "PENDING",
    "created_at": "2026-05-25T12:00:00Z"
  }
  ```
