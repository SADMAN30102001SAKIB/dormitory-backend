"""
Comprehensive API Error Handling Module

This module consolidates all error handling functionality to ensure Django REST API
endpoints always return JSON responses, regardless of the type of error that occurs.

Handles:
- DRF-level exceptions (authentication, permissions, validation, etc.)
- Django-level errors (404, 500, 403, 400)
- Database errors (missing tables, connection issues)
- Server errors and unexpected exceptions
- Custom error formatting with consistent structure

Works in both DEBUG=True (development) and DEBUG=False (production) modes.
"""

import logging

from django.core.exceptions import ValidationError
from django.db import OperationalError
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


# =============================================================================
# DRF CUSTOM EXCEPTION HANDLER
# =============================================================================


def custom_exception_handler(exc, context):
    """
    Custom DRF exception handler that returns JSON responses for all errors.

    Handles:
    - Standard DRF exceptions (authentication, permissions, validation)
    - Database errors (OperationalError, missing tables)
    - Django validation errors
    - Unexpected server errors

    Returns consistent error format:
    {
        "error": true,
        "message": "Human readable error message",
        "details": "Detailed error information",
        "status_code": 400,
        "error_type": "validation_error"
    }
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    # If DRF handled it, modify the response format
    if response is not None:
        custom_response_data = {
            "error": True,
            "message": "Request failed",
            "details": response.data,
            "status_code": response.status_code,
        }

        # Add specific error types for common DRF exceptions
        if hasattr(exc, "__class__"):
            error_name = exc.__class__.__name__
            if "Authentication" in error_name:
                custom_response_data["error_type"] = "authentication_error"
                custom_response_data["message"] = "Authentication required"
            elif "Permission" in error_name:
                custom_response_data["error_type"] = "permission_denied"
                custom_response_data["message"] = "Permission denied"
            elif "Validation" in error_name:
                custom_response_data["error_type"] = "validation_error"
                custom_response_data["message"] = "Validation failed"
            elif "NotFound" in error_name:
                custom_response_data["error_type"] = "not_found"
                custom_response_data["message"] = "Resource not found"
            else:
                custom_response_data["error_type"] = "api_error"

        response.data = custom_response_data
        return response

    # If DRF didn't handle it, create our own response
    custom_response_data = {
        "error": True,
        "message": "An unexpected error occurred",
        "details": str(exc),
        "status_code": 500,
        "error_type": "server_error",
    }

    # Handle specific exception types
    if isinstance(exc, OperationalError):
        if "no such table" in str(exc):
            custom_response_data.update(
                {
                    "message": "Database not properly initialized. Please run migrations.",
                    "details": "Database table missing. Contact administrator.",
                    "status_code": 503,
                    "error_type": "database_error",
                }
            )
            response = Response(
                custom_response_data, status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        else:
            custom_response_data.update(
                {
                    "message": "Database operation failed",
                    "details": "A database error occurred. Please try again later.",
                    "status_code": 503,
                    "error_type": "database_error",
                }
            )
            response = Response(
                custom_response_data, status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

    elif isinstance(exc, ValidationError):
        custom_response_data.update(
            {
                "message": "Validation error",
                "details": str(exc),
                "status_code": 400,
                "error_type": "validation_error",
            }
        )
        response = Response(custom_response_data, status=status.HTTP_400_BAD_REQUEST)

    else:
        # Generic server error
        custom_response_data.update(
            {
                "message": "Internal server error",
                "details": "An unexpected error occurred. Please try again later.",
                "status_code": 500,
                "error_type": "server_error",
            }
        )
        response = Response(
            custom_response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # Log the error for debugging
    logger.error(f"API Error: {exc}", exc_info=True)
    return response


# =============================================================================
# MIDDLEWARE FOR DJANGO-LEVEL ERRORS
# =============================================================================


class ComprehensiveAPIErrorHandler(MiddlewareMixin):
    """
    Universal middleware that ensures all API endpoints return JSON responses for any error.

    This middleware handles Django-level errors that occur before reaching DRF:
    - 404 errors (endpoint not found)
    - 500 errors (server errors)
    - 403 errors (permission denied)
    - 400 errors (bad requests)
    - Any other HTTP errors

    Works in both DEBUG=True and DEBUG=False modes.
    """

    def process_response(self, request, response):
        """
        Convert any HTML error response to JSON for API requests
        """
        # Only process API requests
        if not self._is_api_request(request):
            return response

        # Only process error responses (400+)
        if response.status_code < 400:
            return response

        # Skip if response is already JSON
        content_type = response.get("Content-Type", "")
        if "application/json" in content_type:
            return response

        # Convert HTML error to JSON
        error_data = self._create_error_response(response.status_code, request)
        logger.warning(
            f"API Error converted to JSON: {response.status_code} for {request.path}"
        )

        return JsonResponse(error_data, status=response.status_code)

    def process_exception(self, request, exception):
        """
        Handle any unhandled exceptions for API requests
        """
        # Only handle API requests
        if not self._is_api_request(request):
            return None

        # Let DRF handle its own exceptions first
        if hasattr(request, "resolver_match") and request.resolver_match:
            return None

        # Handle unhandled exceptions
        error_data = self._handle_exception(exception, request)
        logger.error(
            f"Unhandled API exception for {request.path}: {exception}", exc_info=True
        )

        return JsonResponse(error_data, status=error_data["status_code"])

    def _is_api_request(self, request):
        """Check if this is an API request"""
        return request.path.startswith("/api/")

    def _create_error_response(self, status_code, request):
        """Create standardized error response based on status code"""
        error_responses = {
            400: {
                "message": "Bad request",
                "details": "The request could not be understood by the server.",
                "error_type": "bad_request",
            },
            401: {
                "message": "Unauthorized",
                "details": "Authentication is required to access this resource.",
                "error_type": "unauthorized",
            },
            403: {
                "message": "Permission denied",
                "details": "You do not have permission to access this resource.",
                "error_type": "permission_denied",
            },
            404: {
                "message": "Endpoint not found",
                "details": f"The requested endpoint {request.path} does not exist.",
                "error_type": "not_found",
            },
            405: {
                "message": "Method not allowed",
                "details": f"HTTP method {request.method} is not allowed for this endpoint.",
                "error_type": "method_not_allowed",
            },
            500: {
                "message": "Internal server error",
                "details": "An unexpected server error occurred. Please try again later.",
                "error_type": "server_error",
            },
            502: {
                "message": "Bad gateway",
                "details": "The server received an invalid response from an upstream server.",
                "error_type": "bad_gateway",
            },
            503: {
                "message": "Service unavailable",
                "details": "The server is temporarily unavailable. Please try again later.",
                "error_type": "service_unavailable",
            },
        }

        error_info = error_responses.get(
            status_code,
            {
                "message": f"HTTP {status_code} Error",
                "details": "An error occurred while processing your request.",
                "error_type": "http_error",
            },
        )

        return {"error": True, "status_code": status_code, **error_info}

    def _handle_exception(self, exception, request):
        """Handle specific exception types"""
        if isinstance(exception, OperationalError):
            if "no such table" in str(exception):
                return {
                    "error": True,
                    "message": "Database not properly initialized",
                    "details": "Database tables are missing. Please contact administrator or run migrations.",
                    "status_code": 503,
                    "error_type": "database_not_initialized",
                }
            else:
                return {
                    "error": True,
                    "message": "Database operation failed",
                    "details": "A database error occurred. Please try again later.",
                    "status_code": 503,
                    "error_type": "database_error",
                }

        elif isinstance(exception, ValidationError):
            return {
                "error": True,
                "message": "Validation error",
                "details": str(exception),
                "status_code": 400,
                "error_type": "validation_error",
            }

        else:
            # Generic server error
            return {
                "error": True,
                "message": "Internal server error",
                "details": "An unexpected error occurred. Please try again later.",
                "status_code": 500,
                "error_type": "server_error",
            }


def custom_drf_exception_handler(exc, context):
    """
    Custom DRF exception handler that ensures consistent JSON error responses

    This handler is called by Django REST Framework for all exceptions that occur
    within DRF views and serializers.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    # If DRF handled it, enhance the response format
    if response is not None:
        custom_response_data = {
            "error": True,
            "message": _extract_error_message(response.data),
            "details": response.data,
            "status_code": response.status_code,
            "error_type": _determine_error_type(exc, response.status_code),
        }
        response.data = custom_response_data
        return response

    # If DRF didn't handle it, create our own JSON response
    request = context.get("request")
    handler = ComprehensiveAPIErrorHandler()
    error_data = handler._handle_exception(exc, request)

    logger.error(f"DRF unhandled exception: {exc}", exc_info=True)

    return Response(error_data, status=error_data["status_code"])


def _extract_error_message(data):
    """Extract a human-readable error message from DRF error data"""
    if isinstance(data, dict):
        # Common DRF error field names
        for field in ["detail", "message", "error", "non_field_errors"]:
            if field in data:
                error_value = data[field]
                if isinstance(error_value, list) and error_value:
                    return str(error_value[0])
                return str(error_value)

        # If no standard field, return first error found
        for key, value in data.items():
            if isinstance(value, list) and value:
                return f"{key}: {value[0]}"
            return f"{key}: {value}"

    elif isinstance(data, list) and data:
        return str(data[0])

    return str(data) if data else "An error occurred"


def _determine_error_type(exception, status_code):
    """Determine the error type based on exception and status code"""
    exception_name = exception.__class__.__name__.lower()

    error_type_mapping = {
        "authenticationfailed": "authentication_failed",
        "notauthenticated": "not_authenticated",
        "permissiondenied": "permission_denied",
        "notfound": "not_found",
        "methodnotallowed": "method_not_allowed",
        "notacceptable": "not_acceptable",
        "unsupportedmediatype": "unsupported_media_type",
        "throttled": "throttled",
        "validationerror": "validation_error",
        "parseerror": "parse_error",
        "operationalerror": "database_error",
    }

    # Try to match by exception name first
    for exc_name, error_type in error_type_mapping.items():
        if exc_name in exception_name:
            return error_type

    # Fall back to status code mapping
    status_mapping = {
        400: "bad_request",
        401: "unauthorized",
        403: "permission_denied",
        404: "not_found",
        405: "method_not_allowed",
        406: "not_acceptable",
        415: "unsupported_media_type",
        429: "throttled",
        500: "server_error",
        503: "service_unavailable",
    }

    return status_mapping.get(status_code, "api_error")


# Django error handlers for non-DRF requests (when DEBUG=False)
def handler404(request, exception):
    """Custom 404 handler for API requests"""
    if request.path.startswith("/api/"):
        error_data = {
            "error": True,
            "message": "Endpoint not found",
            "details": f"The requested endpoint {request.path} does not exist.",
            "status_code": 404,
            "error_type": "not_found",
        }
        return JsonResponse(error_data, status=404)

    # Let Django handle non-API 404s normally
    from django.views.defaults import page_not_found

    return page_not_found(request, exception)


def handler500(request):
    """Custom 500 handler for API requests"""
    if request.path.startswith("/api/"):
        error_data = {
            "error": True,
            "message": "Internal server error",
            "details": "An unexpected server error occurred. Please try again later.",
            "status_code": 500,
            "error_type": "server_error",
        }
        return JsonResponse(error_data, status=500)

    # Let Django handle non-API 500s normally
    from django.views.defaults import server_error

    return server_error(request)


def handler403(request, exception):
    """Custom 403 handler for API requests"""
    if request.path.startswith("/api/"):
        error_data = {
            "error": True,
            "message": "Permission denied",
            "details": "You do not have permission to access this resource.",
            "status_code": 403,
            "error_type": "permission_denied",
        }
        return JsonResponse(error_data, status=403)

    # Let Django handle non-API 403s normally
    from django.views.defaults import permission_denied

    return permission_denied(request, exception)


def handler400(request, exception):
    """Custom 400 handler for API requests"""
    if request.path.startswith("/api/"):
        error_data = {
            "error": True,
            "message": "Bad request",
            "details": "The request could not be understood by the server.",
            "status_code": 400,
            "error_type": "bad_request",
        }
        return JsonResponse(error_data, status=400)

    # Let Django handle non-API 400s normally
    from django.views.defaults import bad_request

    return bad_request(request, exception)
