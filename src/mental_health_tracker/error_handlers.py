from flask import jsonify, render_template, request
from werkzeug.exceptions import HTTPException
from flask_wtf.csrf import CSRFError
import logging

logger = logging.getLogger(__name__)

def register_error_handlers(app):
    """Register application error handlers."""
    
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        """Custom error handler for CSRF errors."""
        logger.error(f"CSRF error: {str(e)}")
        
        # Check if this is an API request (either API endpoint or requested JSON)
        is_api_request = (
            request.path.startswith('/api') or
            request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
            request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html
        )
        
        if is_api_request:
            return jsonify({
                'error': 'CSRF validation failed',
                'message': str(e)
            }), 400
        
        # Regular HTML response for web pages
        return render_template('errors/csrf_error.html', error=str(e)), 400
    
    @app.errorhandler(404)
    def handle_not_found(e):
        """Custom error handler for 404 errors."""
        logger.warning(f"404 Not Found: {request.path}")
        
        # Check if this is an API request
        is_api_request = (
            request.path.startswith('/api') or
            request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
            request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html
        )
        
        if is_api_request:
            return jsonify({
                'error': 'Not Found',
                'message': f"The requested URL {request.path} was not found on the server."
            }), 404
        
        # Regular HTML response for web pages
        return render_template('errors/404.html', 
                              requested_url=request.path), 404
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        """Generic exception handler."""
        logger.exception(f"Unhandled exception: {str(e)}")
        
        # If it's already an HTTP exception, just pass it on
        if isinstance(e, HTTPException):
            return e
        
        # Check if this is an API request
        is_api_request = (
            request.path.startswith('/api') or
            request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
            request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html
        )
        
        if is_api_request:
            return jsonify({
                'error': 'Internal server error',
                'message': str(e) if app.debug else 'Something went wrong'
            }), 500
        
        # Regular HTML response for web pages
        return render_template('errors/generic_error.html', 
                             error=str(e) if app.debug else 'Something went wrong'), 500 