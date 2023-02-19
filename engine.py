import os
import urllib.request
from typing import Any, Iterable, TypeAlias, Union

import feedparser
import whisper
from algoliasearch.search_client import SearchClient
from dotenv import load_dotenv
from sudachipy import dictionary, tokenizer

Episodes: TypeAlias = Iterable["Episode"]
Nouns: TypeAlias = set[str]


class Episode:
    def __init__(
        self,
        id: str,
        title: str,
        itunes_episode: int,
        summary: str,
        length: str,
        href: str,
        published: str,
    ):
        self.object_id = id
        self.title = title
        self.episode_number = itunes_episode
        self.summary = summary
        self.length = length
        self.media_url = href
        self.published = published
        self.dir = "./media/"

    def _fpath(self) -> str:
        return self.dir + self.object_id + ".music"

    def download_episode(self):
        print("Download: " + self.title)
        data = urllib.request.urlopen(self.media_url).read()
        fpath = self._fpath()
        with open(fpath, mode="wb") as f:
            f.write(data)

    def analyze_media(self, model="medium") -> dict[str, Union[str, Nouns]]:
        print("Start transcription")
        text: str = self._transcription_media(model)
        object = {"content": text}
        print("Start analyze")
        nouns = self._analyze_text(text)
        object |= {"nouns": list(nouns)}
        return object

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

    def post_episode(self, index):
        object = self.analyze_media()
        object |= self._make_object()
        index.save_object(object)

    def _make_object(self) -> dict[str, str | int]:
        return {
            "objectID": self.object_id,
            "title": self.title,
            "episodeNumber": self.episode_number,
            "summary": self.summary,
            "length": self.length,
            "mediaUrl": self.media_url,
            "published": self.published,
        }

    def remove_media(self):
        os.remove(self._fpath())

    def run(self, index):
        print("Start: " + self.title)
        self.post_episode(index)
        self.remove_media()
        print("End: " + self.title)


class Engine:
    def __init__(self):
        load_dotenv()
        self.rss: str = os.getenv("PODCAST_RSS", "")
        self.index_name: str = os.getenv("INDEX_NAME", "")
        self.app_id: str = os.getenv("ALGOLIA_APP_ID", "")
        self.app_key: str = os.getenv("ALGOLIA_APP_KEY", "")
        self.index = self._algolia_index()

    def _algolia_index(self):
        client = SearchClient.create(self.app_id, self.app_key)
        return client.init_index(self.index_name)

    def run(self):
        episodes = self.get_episode()
        recodes = self.get_recodes()
        for episode in episodes:
            if episode.object_id in recodes:
                continue
            episode.download_episode()
            episode.run(self.index)

    def get_episode(self) -> Episodes:
        d = feedparser.parse(self.rss)
        return list(filter(None, [self._transform_entry(entry) for entry in d.entries]))

    def _transform_entry(self, entry: Any) -> Episode:
        links = entry.links
        for link in links:
            if link.rel == "enclosure":
                return Episode(
                    entry.id,
                    entry.title,
                    int(entry.itunes_episode)
                    if entry.has_key("itunes_episode")
                    else "0",
                    entry.summary,
                    entry.itunes_duration,
                    link.href,
                    entry.published,
                )

    def get_recodes(self):
        return [
            id["objectID"]
            for id in self.index.browse_objects({"attributesToRetrieve": ["objectID"]})
        ]
