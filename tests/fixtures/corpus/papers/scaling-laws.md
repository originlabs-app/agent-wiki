# Scaling Laws for Neural Language Models

**Authors:** Kaplan, McCandlish, Henighan, Brown, Chess, Child, Gray, Radford, Wu, Amodei
**Published:** OpenAI, 2020
**arXiv:** 2001.08361

## Key Contribution

Empirically derived power-law relationships between model performance, compute budget, dataset size, and parameter count.

## Core Findings

1. **Performance scales as a power law** with compute, data, and parameters
2. **Larger models are more sample-efficient** — they need less data per parameter
3. **No diminishing returns** — performance continues improving with scale
4. **Six regimes** of scaling based on which resource is the bottleneck

Loss = (X/X_c)^{-alpha} + (Y/Y_c)^{-beta} + (Z/Z_c)^{-gamma} + epsilon_inf

## Implications

Justified the massive investment in larger models (GPT-3, PaLM, Chinchilla)
Showed compute-optimal training ratios (Chinchilla's 20x tokens per parameter)
Predicted capabilities that were later observed at scale

## Relevance to Atlas

Atlas knowledge graph quality should scale with corpus size following similar power laws. This suggests we can benchmark small corpora and predict quality at 10x/100x scale without scanning everything. The "graph saturation" point (when new files add marginal value) is analogous to the knowledge plateau in trained models.
