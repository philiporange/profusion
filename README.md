# Profusion

Profusion is a Python library implementing various Bloom filter types: standard, counting, scalable.

Bloom filters are probabilistic data structures for efficient storage and querying of large datasets, trading accuracy for space. They quickly determine if an element is definitely not in a set - useful for caching, spam filtering, and network routing. Bloom filters save space compared to traditional structures but can't definitively prove set membership, delete elements, or return stored items.

## Installation

```bash
pip install profusion
```

## Usage

Here are examples of how to use the different Bloom filter implementations:

### Standard Bloom Filter

```python
from profusion import Bloom

# Create a new Bloom filter
bf = Bloom(capacity=1000000, error_ratio=1e-5)

# Add elements
bf.add("apple")
bf.add("banana")
bf.add("cherry")

# Check if elements are in the filter
print("apple" in bf)  # True
print("durian" in bf)  # False

# Save the filter to a file
bf.save("bloom_filter.gz")

# Load the filter from a file
bf_loaded = Bloom(path="bloom_filter.gz")

# Check if elements are in the loaded filter
print("banana" in bf_loaded)  # True
print("elderberry" in bf_loaded)  # False
```

### Counting Bloom Filter

```python
from profusion import CountingBloom

# Create a new Counting Bloom filter
cbf = CountingBloom(capacity=1000000, error_ratio=1e-5, bin_size=255)

# Add elements with different counts
cbf.add("apple", amount=3)
cbf.add("banana", amount=2)
cbf.add("cherry", amount=1)

# Check the count of elements
print(cbf.value("apple"))  # 3
print(cbf.value("banana"))  # 2
print(cbf.value("cherry"))  # 1
print(cbf.value("durian"))  # 0

# Check if elements meet a certain threshold
print(cbf.check("apple", trigger=2))  # True
print(cbf.check("banana", trigger=3))  # False

# Add more to an existing element
cbf.add("banana", amount=2)
print(cbf.value("banana"))  # 4
```

### Scalable Bloom Filter

```python
from profusion import ScalableBloom

# Create a new Scalable Bloom filter
sbf = ScalableBloom(max_error=1e-5, initial_size=1024, growth_factor=2)

# Add a large number of elements
for i in range(10000):
    sbf.add(f"element_{i}")

# Check if elements are in the filter
print(sbf.check("element_42"))  # True
print(sbf.check("nonexistent"))  # False

# Demonstrate the scalability
print(f"Number of internal filters: {sbf.blooms}")
print(f"Total capacity: {sbf.threshold}")

# Use check_then_add method
print(sbf.check_then_add("new_element"))  # False (element was not present, but is now added)
print(sbf.check_then_add("new_element"))  # True (element is already present)
```

### Memory-mapped Counting Bloom Filter

```python
from profusion import MMCountingBloom

# Create a new Memory-mapped Counting Bloom filter
mmcbf = MMCountingBloom("my_filter", capacity=1000000, error_ratio=1e-5)

# Add elements
mmcbf.add("apple")
mmcbf.add("banana", amount=2)

# Check the value of elements
print(mmcbf.value("apple"))  # 1
print(mmcbf.value("banana"))  # 2

# Check if elements meet a certain threshold
print(mmcbf.check("apple", trigger=1))  # True
print(mmcbf.check("banana", trigger=3))  # False

# The filter persists across different instances
del mmcbf

# Create a new instance with the same name
mmcbf_2 = MMCountingBloom("my_filter")

# The previously added elements are still present
print(mmcbf_2.value("apple"))  # 1
print(mmcbf_2.value("banana"))  # 2

# Clean up (remove the memory-mapped file)
import os
os.remove(mmcbf_2.path)
```

## License

This project is licensed under the CC0 License.