---
title: Markdown Guide
description: Complete guide to supported Markdown features
tag: reference
---

# Markdown Guide

This page demonstrates all supported Markdown features.

## Text Formatting

You can write **bold**, *italic*, ***bold italic***, ~~strikethrough~~, and ==highlighted== text.

Inline `code` is also supported.

## Links and Images

[Visit GitHub](https://github.com)

## Blockquotes

> This is a blockquote.
> It can span multiple lines.

### Admonitions

> [!NOTE]
> This is a note admonition.

> [!WARNING]
> This is a warning admonition.

> [!IMPORTANT]
> This is an important admonition.

> [!TIP]
> This is a tip admonition.

> [!CAUTION]
> This is a caution admonition.

## Lists

### Unordered List

- Item one
- Item two
- Item three

### Ordered List

1. First
2. Second
3. Third

### Task List

- [x] Completed task
- [ ] Pending task
- [ ] Another task

## Tables

| Feature       | Status   | Notes            |
|:------------- |:--------:| ----------------:|
| Code blocks   | Done     | With highlighting|
| Math formulas | Done     | KaTeX rendering  |
| Tables        | Done     | With alignment   |
| Dark mode     | Done     | Auto-detect      |

## Horizontal Rule

---

## Code Blocks

### JavaScript

```javascript
class EventEmitter {
  constructor() {
    this.events = new Map();
  }

  on(event, callback) {
    if (!this.events.has(event)) {
      this.events.set(event, []);
    }
    this.events.get(event).push(callback);
    return this;
  }

  emit(event, ...args) {
    const callbacks = this.events.get(event);
    if (callbacks) {
      callbacks.forEach(cb => cb(...args));
    }
    return this;
  }
}
```

### Rust

```rust
fn quicksort<T: Ord>(arr: &mut [T]) {
    if arr.len() <= 1 {
        return;
    }
    let pivot = partition(arr);
    quicksort(&mut arr[..pivot]);
    quicksort(&mut arr[pivot + 1..]);
}

fn partition<T: Ord>(arr: &mut [T]) -> usize {
    let len = arr.len();
    let pivot = len - 1;
    let mut i = 0;
    for j in 0..pivot {
        if arr[j] <= arr[pivot] {
            arr.swap(i, j);
            i += 1;
        }
    }
    arr.swap(i, pivot);
    i
}
```

### Go

```go
package main

import (
    "fmt"
    "sync"
)

func fanOut(input <-chan int, workers int) []<-chan int {
    channels := make([]<-chan int, workers)
    for i := 0; i < workers; i++ {
        channels[i] = process(input)
    }
    return channels
}

func process(input <-chan int) <-chan int {
    output := make(chan int)
    go func() {
        defer close(output)
        for n := range input {
            output <- n * n
        }
    }()
    return output
}
```

### C++

```cpp
#include <iostream>

int main(){
    std::cout<<"hello world"<<std::endl;
    return 0;
}
```
