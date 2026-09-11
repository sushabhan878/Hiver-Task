# Brand Selection

Score = 0.30*conv_count + 0.25*resolved_rate + 0.20*message_quality + 0.15*intent_diversity + 0.10*thread_completeness (all normalized to max=1).

| brand | conversations | median turns | brand-reply % | resolved % | intent diversity | score |
|---|---|---|---|---|---|---|
| AmazonHelp | 4000 | 4 | 100% | 63% | 8 | 1.000 |
| XboxSupport | 4000 | 3 | 99% | 52% | 8 | 0.930 |
| British_Airways | 4000 | 3 | 100% | 42% | 8 | 0.893 |
| AskPlayStation | 4000 | 2 | 100% | 44% | 8 | 0.874 |
| AmericanAir | 4000 | 2 | 99% | 41% | 8 | 0.864 |
| AppleSupport | 4000 | 2 | 100% | 39% | 8 | 0.856 |
| SpotifyCares | 4000 | 2 | 100% | 39% | 8 | 0.856 |
| TMobileHelp | 4000 | 2 | 99% | 39% | 8 | 0.855 |
| Uber_Support | 4000 | 2 | 100% | 35% | 8 | 0.838 |
| Delta | 4000 | 2 | 99% | 33% | 8 | 0.830 |

**Selected brand: AmazonHelp** (highest composite score; large volume, near-universal brand-reply rate, diverse intent mix, and multi-turn exchanges suitable for resolution extraction).