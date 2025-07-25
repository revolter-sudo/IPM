# IPM (Infrastructure Project Management) System - Comprehensive Documentation

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture & Technology Stack](#architecture--technology-stack)
3. [Core Features](#core-features)
4. [User Management & Authentication](#user-management--authentication)
5. [Project Management](#project-management)
6. [Payment Processing System](#payment-processing-system)
7. [Khatabook Management](#khatabook-management)
8. [Attendance Management](#attendance-management)
9. [Invoice & PO Management](#invoice--po-management)
10. [Business Logic & Calculations](#business-logic--calculations)
11. [API Documentation](#api-documentation)
12. [Database Schema](#database-schema)
13. [Workflow Diagrams](#workflow-diagrams)
14. [Security & Access Control](#security--access-control)
15. [Deployment & Configuration](#deployment--configuration)

---

## System Overview

The IPM (Infrastructure Project Management) System is a comprehensive web application designed to manage construction and infrastructure projects. It provides end-to-end project lifecycle management including user authentication, project creation, payment processing, attendance tracking, and financial management through an integrated khatabook system.

### Key Business Domains

1. **Project Management**: Create and manage construction projects with multiple Purchase Orders (POs)
2. **Payment Processing**: Handle payment requests, approvals, and transfers with multi-level approval workflows
3. **Khatabook System**: Financial ledger system for tracking expenses and credits
4. **Attendance Management**: Track both self-attendance and project worker attendance
5. **Invoice Management**: Handle client invoices and payment tracking
6. **User & Role Management**: Multi-role user system with granular permissions
7. **Machinery Management**: Track and manage construction equipment

### Target Users

- **Super Admin**: Full system access and configuration
- **Admin**: Administrative functions and oversight
- **Accountant**: Financial operations and payment processing
- **Project Manager**: Project oversight and team management
- **Site Engineer**: Field operations and attendance tracking

---

## Architecture & Technology Stack

### Backend Architecture

The system follows a **layered architecture** pattern with clear separation of concerns:

```
┌─────────────────────────────────────────┐
│              Presentation Layer          │
│         (FastAPI Routers & Endpoints)   │
├─────────────────────────────────────────┤
│              Business Logic Layer       │
│            (Service Classes)            │
├─────────────────────────────────────────┤
│              Data Access Layer          │
│         (SQLAlchemy Models & ORM)       │
├─────────────────────────────────────────┤
│              Database Layer             │
│            (PostgreSQL)                 │
└─────────────────────────────────────────┘
```

### Technology Stack

#### Core Framework
- **FastAPI**: Modern, fast web framework for building APIs with Python
- **Python 3.8+**: Programming language
- **Uvicorn**: ASGI server for running the application

#### Database & ORM
- **PostgreSQL**: Primary relational database
- **SQLAlchemy**: ORM for database operations
- **Alembic**: Database migration tool

#### Authentication & Security
- **JWT (JSON Web Tokens)**: Stateless authentication
- **Passlib + Bcrypt**: Password hashing
- **Firebase Admin SDK**: Push notifications

#### Caching & Performance
- **Redis**: Caching layer for improved performance
- **FastAPI Cache**: Caching middleware

#### File Storage & Uploads
- **Local File System**: Document and image storage
- **Static File Serving**: FastAPI StaticFiles for file access

#### Additional Services
- **SMS Service**: User verification and notifications
- **Location Service**: GPS-based attendance validation
- **Logging System**: Comprehensive application logging

### Project Structure

```
src/app/
├── main.py                 # Application entry point
├── database/
│   ├── database.py         # Database configuration
│   └── models.py          # SQLAlchemy models
├── services/              # Business logic layer
│   ├── auth_service.py    # Authentication & user management
│   ├── project_service.py # Project management
│   ├── payment_service.py # Payment processing
│   ├── khatabook_service.py # Financial ledger
│   ├── attendance_service.py # Attendance tracking
│   └── ...
├── schemas/               # Pydantic models for validation
├── middleware/            # Custom middleware
├── utils/                 # Utility functions
├── admin_panel/          # Admin interface
└── templates/            # HTML templates
```

---

## Core Features

### 1. Multi-Role User Management
- **Role-based access control** with 5 distinct user roles
- **JWT-based authentication** with token management
- **SMS verification** for user registration
- **User profile management** with photo uploads

### 2. Project Lifecycle Management
- **Multi-PO project creation** with document uploads
- **Project-user-item mapping** for resource allocation
- **Project balance tracking** (estimated vs actual)
- **Project status management** throughout lifecycle

### 3. Advanced Payment System
- **Multi-level approval workflow** (Requested → Verified → Approved → Transferred)
- **Self-payment functionality** for site engineers
- **Payment file attachments** and documentation
- **Integration with khatabook** for financial tracking
- **Bank account management** for payment processing

### 4. Comprehensive Attendance System
- **Self-attendance** with GPS validation for site engineers
- **Project attendance** for tracking worker/laborer attendance
- **Daily wage management** with configurable rates
- **Attendance analytics** and reporting

### 5. Financial Management (Khatabook)
- **Dual-entry system** (Debit/Credit entries)
- **Automatic integration** with self-payment approvals
- **File attachments** for expense documentation
- **Balance calculations** and tracking
- **Role-based visibility** controls

### 6. Invoice & PO Management
- **Multiple PO support** per project
- **Invoice creation** linked to specific POs
- **Payment tracking** for invoices
- **Late payment detection** and analytics

### 7. Machinery & Equipment Management
- **Equipment tracking** and assignment
- **Project-based machinery allocation**
- **Usage monitoring** and reporting

---
