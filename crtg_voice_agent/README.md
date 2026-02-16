# Voice Agent

A production-ready AI-powered real estate appointment booking system built with FastAPI, Groq, Deepgram, and Twilio.

## Features

### 🤖 AI-Powered Conversations
- **Reduced Hallucination**: Advanced prompt engineering and response validation
- **Structured Data Extraction**: Automatic extraction of names, emails, and property preferences
- **Context Management**: Intelligent conversation flow with history limiting
- **Multi-language Support**: Built-in support for international property markets

### 📞 Production-Ready Call Handling
- **WebSocket Streaming**: Real-time bidirectional audio streaming
- **Error Recovery**: Automatic reconnection and retry logic for all services
- **Security**: Twilio request validation and CORS protection
- **Monitoring**: Comprehensive logging and health checks

### 🎯 Real Estate Specific
- **Property Flow**: Structured booking flow (buy/rent → location → type → budget → time)
- **Email Integration**: Automated appointment confirmation emails with HTML templates
- **Lead Management**: Structured lead data storage and retrieval
- **Multi-voice TTS**: Professional voice options with fallback mechanisms

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Twilio Call   │───▶│   FastAPI App    │───▶│   GPT Logic     │
│   (Inbound)     │    │   (WebSocket)    │    │   (Groq API)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Deepgram      │◀───│   Transcriber    │◀───│   TTS Engine    │
│   (STT)         │    │   (Real-time)    │    │   (Deepgram)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌──────────────────┐
│   PostgreSQL    │◀───│   Database       │
│   (Async)       │    │   (SQLAlchemy)   │
└─────────────────┘    └──────────────────┘
```

## Quick Start

### 1. Environment Setup

```bash
# Clone and install dependencies
git clone <repository-url>
cd voice_agent
pip install -r requirements.txt

# Create environment file
cp .env.example .env
```

### 2. Environment Configuration

```bash
# Required API Keys
GROQ_API_KEY=your_groq_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token

# Optional Configuration
DEEPGRAM_TTS_VOICE=aura-athena-en  # British female (most natural)
COMPANY_NAME="Your Real Estate Company"
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
FROM_EMAIL=noreply@yourcompany.com
```

### 3. Database Setup

```bash
# Initialize database
alembic upgrade head
```

### 4. Run the Application

```bash
# Development
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production
python main.py
```

### 5. Configure Twilio

1. Set your Twilio phone number's webhook to: `https://your-domain.com/incoming-call`
2. Configure WebSocket URL: `wss://your-domain.com/media-stream`

## API Endpoints

### Health Check
```http
GET /health
```

### Call Management
```http
POST /incoming-call     # Twilio webhook for incoming calls
WebSocket /media-stream # Real-time audio streaming
```

### Monitoring
```http
GET /metrics           # Application metrics
GET /docs             # Interactive API documentation
```

## Production Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "main.py"]
```

### Environment Variables for Production

```bash
# Security
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com
CORS_ORIGINS=https://yourdomain.com

# Performance
WORKERS=4
MAX_CALL_DURATION=300
MAX_TRANSCRIPTION_RETRIES=3

# Monitoring
LOG_LEVEL=INFO
ENABLE_METRICS=true
```

### Load Balancing

For high availability, deploy behind a load balancer with:

- **Session Affinity**: Required for WebSocket connections
- **Health Checks**: Use `/health` endpoint
- **SSL Termination**: Handle at load balancer level

## Error Handling & Monitoring

### Error Categories

1. **API Errors**: Rate limits, timeouts, authentication failures
2. **Network Errors**: Connection drops, WebSocket failures
3. **Audio Errors**: Transcription failures, TTS generation issues
4. **Database Errors**: Connection failures, constraint violations

### Monitoring

- **Structured Logging**: All components log to structured format
- **Performance Metrics**: Response times, error rates, call durations
- **Health Checks**: Service availability monitoring
- **Error Tracking**: Detailed error logging with context

### Alerting

Set up alerts for:
- High error rates (>5%)
- Long response times (>3 seconds)
- Service unavailability
- Database connection issues

## Security

### Authentication
- Twilio request validation using HMAC signatures
- API key management for external services

### Data Protection
- Encrypted database connections
- Secure credential storage
- Input validation and sanitization

### Rate Limiting
- Built-in retry logic with exponential backoff
- Connection pooling for database operations
- WebSocket connection limits

## Testing

### Unit Tests
```bash
pytest tests/unit/
```

### Integration Tests
```bash
pytest tests/integration/
```

### Load Testing
```bash
# Test with multiple concurrent calls
pytest tests/load/ --concurrent
```

## Troubleshooting

### Common Issues

1. **WebSocket Connection Drops**
   - Check network stability
   - Verify Twilio configuration
   - Monitor server resources

2. **Poor Transcription Quality**
   - Verify audio quality
   - Check Deepgram API limits
   - Consider model selection

3. **TTS Failures**
   - Check Deepgram API key
   - Verify voice model availability
   - Monitor fallback mechanisms

4. **Database Issues**
   - Check connection pool settings
   - Monitor query performance
   - Verify migrations are applied

### Debug Mode

Enable debug logging:
```bash
LOG_LEVEL=DEBUG
DEBUG=true
```

### Performance Tuning

1. **Database**
   - Use connection pooling
   - Optimize query patterns
   - Add appropriate indexes

2. **API Calls**
   - Implement caching where appropriate
   - Use connection pooling for HTTP
   - Monitor API rate limits

3. **Audio Processing**
   - Optimize audio chunk sizes
   - Use appropriate compression
   - Monitor memory usage

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for your changes
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Review the troubleshooting guide

## Changelog

### v1.0.0
- Initial production release
- Hallucination reduction features
- Comprehensive error handling
- Production deployment guide