# Glossary

- High price: Average or observed sell-side price from source high channel.
- Low price: Average or observed buy-side price from source low channel.
- Mid-price: (avg_high_price + avg_low_price) / 2 when both values are present and valid.
- Spread: Difference between high and low price.
- Volume: Quantity traded in an interval (high and low channels tracked separately).
- Interval: Aggregation granularity such as latest, 5m, or 1h.
- Forecast horizon: Time distance from forecast creation to target timestamp.
- Walk-forward validation: Time-aware evaluation where train/test windows move forward chronologically.
- Champion model: Selected best-performing model for an item and horizon under defined rules.
- Challenger model: Candidate model evaluated against current champion.
- Liquidity: Practical tradability reflected by volume and spread behavior.
- Data freshness: How current source observations are relative to present time.
- GE buy limit: Grand Exchange limit controlling purchasable amount in a rolling period.
