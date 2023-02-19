# engine.py

RSSフィードからポッドキャストの音声をダウンロードし、Algoliaへインデックスを追加するスクリプト

## 使い方

```python
python main.py
```

## 導入方法
1. NVIDIAのDriverを入れる（[https://www.nvidia.com/Download/index.aspx?lang=jp]()）
1. CUDA Toolkitを入れる（[https://developer.nvidia.com/cuda-downloads]()）
1. cuDNNを入れる（[https://developer.nvidia.com/rdp/cudnn-download]()）
1. NCCLを入れる（[https://developer.nvidia.com/nccl/nccl-download]()）
1. FFmpegを入れる
    ```bash
    sudo apt update
    sudo apt upgrade
    sudo apt install ffmpeg
    ```
1. Pythonの仮想環境を起動し、ライブラリを入れる
    ```bash
    poetry update
    ```