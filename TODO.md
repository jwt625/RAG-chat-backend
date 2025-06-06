# TODO.md

## Production Readiness Items - December 6, 2024

### Missing Production Dependencies ✅ COMPLETED
~~Add to `requirements.txt`:~~
- ✅ `sentry-sdk==2.29.1` - For error monitoring integration
- ✅ `slowapi==0.1.9` - For rate limiting middleware  
- ✅ `psutil==7.0.0` - For system monitoring utilities
- ✅ `PyJWT==2.10.1` - For JWT authentication

### Configuration TODOs
- **Sentry DSN**: Configure Sentry error tracking DSN in `app/production.py:31`
- **Trusted Hosts**: Set allowed host domains in `app/production.py:48`
- **API Key Validation**: Implement API key validation against database in `app/security.py:24`

### Production Deployment
- Complete production configuration setup
- Test production mode with `app/production.py`
- Verify all security middleware is functioning
- Set up monitoring and alerting