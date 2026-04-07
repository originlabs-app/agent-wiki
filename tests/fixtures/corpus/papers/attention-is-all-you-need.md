# Attention Is All You Need

**Authors:** Vaswani, Shazeer, Parmar, Uszkoreit, Jones, Gomez, Kaiser, Polosukhin
**Published:** NeurIPS 2017
**arXiv:** 1706.03762

## Key Contribution

Introduced the Transformer architecture, replacing recurrence and convolution with self-attention as the primary mechanism for sequence modeling.

## Core Ideas

1. **Self-Attention**: Each token attends to all other tokens, computing weighted combinations
2. **Multi-Head Attention**: Multiple attention heads capture different types of relationships
3. **Positional Encoding**: Sinusoidal encodings inject position information into the model
4. **Encoder-Decoder**: Stack of identical encoder/decoder layers with residual connections

Key equation — scaled dot-product attention:
```
Attention(Q, K, V) = softmax(QK^T / sqrt(d_k)) V
```

## Impact

- Foundation for GPT, BERT, and all modern LLMs
- Enabled training scaling (billions of parameters)
- O(1) sequential computation vs O(n) for RNNs

## Relevance to Atlas

Atlas uses similar principles: the knowledge graph creates "attention" between concepts via edges, and community detection is analogous to multi-head attention discovering different relationship types between code entities.
