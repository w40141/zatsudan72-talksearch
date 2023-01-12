import urllib.request
import feedparser
from dotenv import load_dotenv
from typing import Any
import os
import whisper
from sudachipy import tokenizer
from sudachipy import dictionary
from algoliasearch.search_client import SearchClient


class Engine:
    def __init__(self):
        load_dotenv()
        self.rss = os.getenv("PODCAST_RSS", "")
        self.index_name = os.getenv("INDEX_NAME", "")
        self.app_id = os.getenv("ALGOLIA_APP_ID", "")
        self.app_key = os.getenv("ALGOLIA_APP_KEY", "")

    # 1. RSSからエピソードの取得する
    def get_episode(self) -> Any:
        d = feedparser.parse(self.rss)
        return {entry.id: self._transform_entry(entry) for entry in d.entries}

    def _transform_entry(self, entry: Any):
        e = {}
        links = entry.links
        for link in links:
            if link.ref == "enclosure":
                e = {
                    "episode_id": entry.id,
                    "title": entry.title,
                    "episode_number": entry.itunes_episode
                    if entry.has("itunes_episode")
                    else 0,
                    "media_url": link.ref,
                    "published": entry.published,
                }
            break
        return e

    # 2. エピソードをダウンロードする
    def download_episodes(self, episodes: dict[str, dict[str, str]]):
        recodes = self._get_recodes()
        for key, episode in episodes.values():
            if key not in recodes:
                self._download_episode(episode)

    # 2-1. indexを取得する
    def _get_recodes(self):
        # Use an API key with `browse` ACL
        client = SearchClient.create(self.app_id, self.app_key)
        index = client.init_index(self.index_name)
        return list(index.browse_objects({"attributesToRetrieve": ["episode_id"]}))

    # 2-2. ダウンロードする
    def _download_episode(self, episode):
        urllib.request.urlretrieve(
            episode["media_url"], self._media_path(episode["number"])
        )

    def _media_path(self, number: str, path="media") -> str:
        return path + "{:04}".format(number)

    # 3. 文字起こしする
    def transcription_media(self, fname: str, model="small") -> str:
        model = whisper.load_model(model)
        result = model.transcribe(fname, language="ja")
        return result["text"]

    # 4. 形態素解析する
    def analyse_text(self, text: str) -> set[str]:
        mode = tokenizer.Tokenizer.SplitMode.C
        tokenizer_obj = dictionary.Dictionary().create()
        tokens = tokenizer_obj.tokenize(text, mode)
        return set(
            [token.surface() for token in tokens if token.part_of_speech()[0] == "名詞"]
        )

    # 5. Algoliaへデータを投入する
    def post_nouns(episode: Any, nouns: set[str]):
        pass
