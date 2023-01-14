import os
import urllib.request
from typing import Any, Iterable, TypeAlias

import feedparser
import whisper
from algoliasearch.search_client import SearchClient
from dotenv import load_dotenv
from sudachipy import dictionary, tokenizer

Episodes: TypeAlias = Iterable["Episode"]
Nouns: TypeAlias = set[str]


class Episode:
    def __init__(
        self, id: str, title: str, itunes_episode: str, href: str, published: str
    ):
        self.object_id = id
        self.title = title
        self.episode_number = itunes_episode
        self.media_url = href
        self.published = published
        self.dir = "./media/"

    def _fpath(self) -> str:
        return self.dir + self.object_id + ".music"

    def download_episode(self):
        data = urllib.request.urlopen(self.media_url).read()
        fpath = self._fpath()
        with open(fpath, mode="wb") as f:
            f.write(data)

    def analyze_media(self, model="medium") -> Nouns:
        print("Start transcription")
        text: str = self._transcription_media(model)
        print("Start analyze")
        return self._analyze_text(text)

    def _transcription_media(self, model) -> str:
        model = whisper.load_model(model)
        fpath = self._fpath()
        result = model.transcribe(fpath, language="ja")
        return result["text"]

    def _analyze_text(self, text: str) -> Nouns:
        mode = tokenizer.Tokenizer.SplitMode.C
        tokenizer_obj = dictionary.Dictionary().create()
        tokens = tokenizer_obj.tokenize(text, mode)
        return set(
            [token.surface() for token in tokens if token.part_of_speech()[0] == "名詞"]
        )

    def post_episode(self, index, nouns: Nouns):
        object = self._make_object() | {"nouns": list(nouns)}
        index.save_object(object)

    def _make_object(self) -> dict[str, str]:
        return {
            "objectID": self.object_id,
            "title": self.title,
            "episodeNumber": self.episode_number,
            "mediaUrl": self.media_url,
            "published": self.published,
        }

    def remove_media(self):
        os.remove(self._fpath())


class Engine:
    def __init__(self):
        load_dotenv()
        self.rss: str = os.getenv("PODCAST_RSS", "")
        self.index_name: str = os.getenv("INDEX_NAME", "")
        self.app_id: str = os.getenv("ALGOLIA_APP_ID", "")
        self.app_key: str = os.getenv("ALGOLIA_APP_KEY", "")
        self.dir = "./media/"

    def algolia_index(self):
        client = SearchClient.create(self.app_id, self.app_key)
        return client.init_index(self.index_name)

    def run(self):
        episodes = self.get_episode()
        downloaded_episodes = self.download_episodes(episodes)
        index = self.algolia_index()
        for episode in downloaded_episodes:
            self._run_episode(episode, index)

    def _run_episode(self, episode, index):
        print("Start: " + episode.title)
        nouns = episode.analyze_media()
        episode.post_episode(index, nouns)
        episode.remove_media()
        print("End: " + episode.title)

    def get_episode(self) -> Episodes:
        d = feedparser.parse(self.rss)
        return list(filter(None, [self._transform_entry(entry) for entry in d.entries]))

    def _transform_entry(self, entry: Any) -> Any:
        links = entry.links
        for link in links:
            if link.rel == "enclosure":
                return Episode(
                    entry.id,
                    entry.title,
                    entry.itunes_episode if entry.has_key("itunes_episode") else "0",
                    link.href,
                    entry.published,
                )

    def download_episodes(self, episodes: Episodes) -> Episodes:
        recodes = self._get_recodes()
        downloaded_episodes = []
        for episode in episodes:
            object_id = episode.object_id
            if object_id not in recodes:
                print("Download: " + episode.title)
                episode.download_episode()
                downloaded_episodes.append(episode)
        return downloaded_episodes

    def _get_recodes(self):
        index = self.algolia_index()
        return [
            id["objectID"]
            for id in index.browse_objects({"attributesToRetrieve": ["objectID"]})
        ]
