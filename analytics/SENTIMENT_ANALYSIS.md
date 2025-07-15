# Sentiment Analysis with VADER

This implementation adds comprehensive sentiment analysis capabilities to the GovStack analytics module using VADER (Valence Aware Dictionary and sEntiment Reasoner).

## Overview

VADER is a rule-based sentiment analysis tool that's particularly effective for:
- Social media text and informal language
- Short text messages like chat conversations
- Text containing slang, emojis, and abbreviations
- Real-time sentiment analysis without requiring training data

## Features Implemented

### 1. Sentiment Analysis Utility (`sentiment_analyzer.py`)

The `SentimentAnalyzer` class provides:
- **Basic sentiment analysis**: Returns sentiment scores for negative, neutral, positive, and compound sentiment
- **Sentiment classification**: Categorizes text as positive, negative, or neutral based on compound scores
- **Satisfaction scoring**: Converts sentiment to a 1-5 satisfaction scale
- **Escalation detection**: Identifies messages that may require human intervention

### 2. Enhanced Analytics Service

Added `get_user_sentiment()` method to `AnalyticsService` that:
- Analyzes all user messages in a specified time period
- Calculates conversation-level sentiment patterns
- Provides escalation rate metrics
- Returns detailed sentiment distribution statistics

### 3. Updated API Endpoint

The `/sentiment` endpoint now provides real sentiment analysis instead of placeholder data:
- Analyzes actual user message content
- Returns comprehensive sentiment metrics
- Supports date range filtering
- Provides actionable insights for customer service improvement

## Sentiment Score Interpretation

### Compound Score Ranges
- **Positive**: compound score ≥ 0.05
- **Neutral**: -0.05 < compound score < 0.05  
- **Negative**: compound score ≤ -0.05

### Satisfaction Score Conversion
- Compound score -1.0 → Satisfaction 1.0 (Very Dissatisfied)
- Compound score 0.0 → Satisfaction 3.0 (Neutral)
- Compound score 1.0 → Satisfaction 5.0 (Very Satisfied)

### Escalation Threshold
- Messages with compound score ≤ -0.5 are flagged for potential escalation
- This threshold can be adjusted based on business requirements

## Usage Examples

### Basic Sentiment Analysis
```python
from sentiment_analyzer import sentiment_analyzer

# Analyze a single message
scores, classification = sentiment_analyzer.analyze_and_classify("This service is great!")
# Returns: ({'neg': 0.0, 'neu': 0.294, 'pos': 0.706, 'compound': 0.6249}, 'positive')

# Check satisfaction score
satisfaction = sentiment_analyzer.calculate_satisfaction_score(0.6249)
# Returns: 4.2
```

### API Usage
```bash
# Get sentiment analysis for the last 30 days
GET /analytics/user/sentiment

# Get sentiment for specific date range
GET /analytics/user/sentiment?start_date=2025-01-01&end_date=2025-01-31
```

## Response Schema

```json
{
  "positive_conversations": 150,
  "negative_conversations": 25,
  "neutral_conversations": 75,
  "satisfaction_score": 4.1,
  "escalation_rate": 8.2,
  "average_sentiment_score": 0.234,
  "total_analyzed_messages": 1250,
  "sentiment_distribution": [
    {
      "category": "Positive",
      "count": 750,
      "percentage": 60.0
    },
    {
      "category": "Neutral", 
      "count": 350,
      "percentage": 28.0
    },
    {
      "category": "Negative",
      "count": 150,
      "percentage": 12.0
    }
  ]
}
```

## Installation

Add to your requirements.txt:
```
vaderSentiment==3.3.2
```

Install the package:
```bash
pip install vaderSentiment
```

## Testing

Run the demo script to test sentiment analysis:
```bash
cd analytics
python test_sentiment_demo.py
```

## Business Value

### Customer Service Insights
- **Proactive Support**: Identify frustrated users before they escalate
- **Quality Monitoring**: Track satisfaction trends over time
- **Response Optimization**: Understand which interactions create positive vs negative sentiment

### Product Improvement
- **Feature Impact**: Measure sentiment changes after feature releases
- **Content Quality**: Identify knowledge gaps that cause user frustration
- **User Experience**: Track sentiment patterns to improve conversation flows

### Operational Metrics
- **Escalation Prevention**: Reduce human handoff needs through early intervention
- **Performance Benchmarking**: Set sentiment-based KPIs for chatbot performance
- **Training Data**: Use sentiment patterns to improve AI responses

## Considerations

### Accuracy
- VADER is highly effective for informal text but may miss context-specific sentiment
- Consider domain-specific fine-tuning for specialized terminology
- Combine with human review for critical escalation decisions

### Performance
- VADER is fast and doesn't require GPU resources
- Sentiment analysis adds minimal processing overhead
- Consider caching results for frequently accessed time periods

### Privacy
- Sentiment analysis processes message content
- Ensure compliance with data privacy regulations
- Consider anonymization for long-term sentiment trend storage
