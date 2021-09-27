import asyncio
import requests
import re
import string
import random
from yukinoshita.Yukinoshita.downloader import Downloader

def int2base(x, base):
        digs = string.digits + string.ascii_letters
        if x < 0:
            sign = -1
        elif x == 0:
            return digs[0]
        else:
            sign = 1
        x *= sign
        digits = []
        while x:
            digits.append(digs[int(x % base)])
            x = int(x / base)
        if sign < 0:
            digits.append("-")
        digits.reverse()
        return "".join(digits)

def js_unpack(p, a, c, k):
    k = k.split("|")
    a = int(a)
    c = int(c)
    d = {}
    while c > 0:
        c -= 1
        d[int2base(c, a)] = k[c]
    for x in d:
        if d[x] == "":
            d[x] = x
        p = re.sub(f"\\b{x}\\b", d[x], p)
    return p

class AnimePahe:
    def __init__(self, domain: str = "https://animepahe.org") -> None:
        self.domain = domain
        self.session = requests.session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:94.0) Gecko/20100101 Firefox/94.0"
            }
        )
        self.__get_ddos_guard_cookie()

    def __get_ddos_guard_cookie(self) -> None:
        self.session.get(
            "https://animepahe.org/.well-known/ddos-guard/id/"
            + "".join(
                random.choice(string.ascii_letters + string.digits) for _ in range(12)
            )
        )

    def __minify_text(self, text: str) -> str:
        return re.sub(r"\s+", "", text).strip()

    def __get_minified(self, path: str) -> str:
        return self.__get_minified_uri(f"{self.domain}{path}")

    def __get_minified_uri(self, uri: str, headers: dict = None) -> str:
        return self.__minify_text(self.session.get(uri, headers=headers).text)

    def __get_api(self, data: dict) -> str:
        return self.session.get(f"{self.domain}/api", params=data).json()

    def get_real_anime_id(self, anime_uuid: str) -> int:
        rx = re.compile(
            r"\$\.getJSON\('/api\?m=release&id=(.*?)&sort='\+sort\+'&page='\+page,function\(data"
        )
        r = rx.search(self.__get_minified(f"/anime/{anime_uuid}"))
        return int(r.group(1))

    def get_episodes(self, anime_id: int, page: int = 1) -> list:
        episode_ids = []
        data  = self.__get_api({"m": "release", "sort": "episode_desc", "id": anime_id, "page": page})
        episode_ids += [x["session"] for x in data["data"]]
        if data["last_page"] > page:
            episode_ids += self.get_episodes(anime_id, page + 1)
   
        return episode_ids
    
    def get_links(self, anime_id: int, episodes: list) -> list:
        links = []
        for episode in episodes:
            data = self.__get_api(
                {"m": "links", "id": anime_id, "session": episode, "p": "kwik"}
            )
            for x in data["data"]:
                best_q = 0
                for xx in x:
                    if int(xx) > best_q:
                        best_q = int(xx)
                links.append(x[str(best_q)]["kwik"])
        return links

    def get_hls_playlist(self, kwik_link: str) -> dict:
        data = self.__get_minified_uri(kwik_link, headers={"Referer": self.domain})
        rx = re.compile(r"returnp}\('(.*?)',(\d\d),(\d\d),'(.*?)'.split")
        title_re = re.compile(r"<title>(.*?)</title>")
        title = title_re.search(data).group(1)
        r = rx.findall(data)
        x = r[-1]
        unpacked = js_unpack(x[0], x[1], x[2], x[3])
        stream_re = re.compile(r"https:\/\/(.*?)uwu.m3u8")
        return {"file_name": title, "url": stream_re.search(unpacked).group(0)}

    async def download(self, hls_url, file_name):
        m3u8 = self.session.get(hls_url, headers={"Referer": "https://kwik.cx"}).text
        await Downloader(m3u8, file_name).run()
    
    def dl(self, e):
        print("Downloading " + e["file_name"])
        asyncio.run(client.download(e["url"], e["file_name"]))

print("Setting up the client.")
client = AnimePahe()
url = input("AnimePahe anime url: ")
anime_id = client.get_real_anime_id(url.split("/")[-1])
eps = client.get_episodes(anime_id)

links = client.get_links(anime_id, eps)
for link in links:
    hls_playlist = client.get_hls_playlist(link)
    client.dl(hls_playlist)