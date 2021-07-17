from bs4 import BeautifulSoup
import copy
import matplotlib.pyplot as plt
import random
import requests
import re
import telebot

TOKEN = ''

class UserMusicData:
    '''
    artists:
    artist_id: {name, genre}
    tracks:
    track:album : name, genre, artist_id, artist_name
    '''

    TOP_GENRES = 5  # use it while calculating the match probability

    def __init__(self, user_id, artists, tracks):
        self.user_id = user_id
        self.artists = artists
        self.tracks = tracks
        for track_id, track in self.tracks.items():
            self.artists[track.get("artist_id")] = {'name': str(track.get('artist_name')), 'genre': str(track.get('genre'))}

    @staticmethod
    def from_url(user_id):
        return UserMusicData(user_id,
                             UserMusicData.get_favourite_artists(user_id),
                             UserMusicData.get_favourite_tracks(user_id))

    @staticmethod
    def get_artist_genre(artist_id) -> str:
        url = 'https://music.yandex.ru/artist/' + artist_id
        try:
            response = requests.get(url)
        except:
            return None
        soup = BeautifulSoup(response.content, 'lxml')
        try:
            genre = dict(eval(soup.script.string)).get("genre")
        except:
            genre = None
        return genre

    @staticmethod
    def get_favourite_artists(user_id) -> dict:
        url = 'https://music.yandex.ru/users/' + user_id + '/artists'
        try:
            response = requests.get(url)
        except:
            return None
        soup = BeautifulSoup(response.content, 'lxml')
        # print(soup.prettify())
        artists = dict()
        for artist_block in soup.find_all('div', 'artist__name deco-typo typo-main'):
            name = artist_block.get('title')
            link = artist_block.a.get('href')
            id = link.split('/')[-1]
            genre = UserMusicData.get_artist_genre(id)
            artists[id] = dict({"name": name, "genre": genre})
        return artists

    @staticmethod
    def get_favourite_tracks(user_id) -> dict:
        url = 'https://music.yandex.ru/users/' + user_id + '/playlists/3'
        try:
            response = requests.get(url)
        except:
            return None
        soup = BeautifulSoup(response.content, 'lxml')
        pos = soup.body.script.string.find("trackIds")
        # track:album
        track_ids = re.findall('\d+:\d+', soup.body.script.string[pos:])
        tracks = dict()
        for track_id in track_ids:
            track, album = track_id.split(':')
            track_url = 'https://music.yandex.ru/album/' + album + '/track/' + track
            try:
                response = requests.get(track_url)
            except:
                continue
            soup = BeautifulSoup(response.content, 'lxml')
            try:
                track_properties = dict(eval(soup.script.string))
            except:
                continue
            name = track_properties.get('name')
            inAlbum = track_properties.get('inAlbum')
            genre = None
            if ((inAlbum is None) == False):
                genre = inAlbum.get('genre')
            byArtist = track_properties.get('byArtist')
            artist_id = None
            artist_name = None
            if ((byArtist is None) == False):
                artist_id = byArtist.get('url').split('/')[-1]
                artist_name = byArtist.get('name')
            if ((name is None) == False and (artist_id is None) == False):
                tracks[track_id] = {"name": name, "genre": genre, "artist_id": artist_id, "artist_name": artist_name}
        return tracks

    @staticmethod
    def get_favourite_genres(self):
        count = dict()
        for id, track in self.tracks.items():
            if (track.get('genre') is None):
                continue
            try:
                value = count.get(track.get('genre'), 0)
                count[track.get('genre')] = value + 1
            except:
                continue
        labels = list()
        counts = list()
        for k in sorted(count, key=count.get, reverse=True):
            labels.append(k)
            counts.append(count.get(k))
        return (labels, counts)

    def get_genre_pie_image(self) -> str:
        labels, counts = self.get_favourite_genres(self)
        fig1, ax1 = plt.subplots()
        fig1.set_size_inches(10, 10)
        img = self.user_id + '_genres_chart.png'
        ax1.pie(counts, shadow=False, startangle=90, normalize=True)
        ax1.axis('equal')
        plt.legend(labels=labels)
        plt.show()
        fig1.savefig(img, dpi=100)
        return img

    def get_top_genres(self):
        genres, cnts = self.get_favourite_genres(self)
        top_genres = dict()
        for i in range(len(genres)):
            top_genres[genres[i]] = i
        return top_genres

    def get_fav_artist(self):
        count = dict()
        for track_id, track_info in self.tracks.items():
            try:
                value = count.get(track_info.get('artist_name'), 0)
                count[track_info.get('artist_name')] = value + 1
            except:
                continue
        for k in sorted(count, key=count.get, reverse=True):
            return k

    def calc_track_match_probability(self, track_id, track_info, fav_genres) -> float:
        if ((self.tracks.get(track_id) is None) == False):
            return 1
        if ((self.artists.get(track_info.get('artist_id')) is None) == False):
            if (track_info.get('genre') is None):
                return 0.5
            top = fav_genres.get(track_info.get('genre'))
            if (top is None):
                return 0.5
            if (top < self.TOP_GENRES):
                return 0.8
            return 0.6
        if (track_info.get('genre') is None):
            return 0.3
        top = fav_genres.get(track_info.get('genre'))
        if (top is None):
            return 0.15
        if (top < self.TOP_GENRES):
            return 0.7
        if (top < self.TOP_GENRES * 2):
            return 0.6
        if (top < self.TOP_GENRES * 3):
            return 0.5
        return 0.15


class UsersMatch:

    def __init__(self, user1, user2):
        self.user1 = user1
        self.user2 = user2

    def precise_track_intersection(self) -> dict:
        intersection = self.user1.tracks.keys() & self.user2.tracks.keys()
        result = list()
        for k in intersection:
            result.append((k, self.user1.tracks.get(k)))
        return dict(result)

    def precise_artist_intersection(self) -> dict:
        intersection = self.user1.artists.keys() & self.user2.artists.keys()
        result = list()
        for k in intersection:
            result.append((k, self.user1.artists.get(k)))
        return dict(result)

    def calc_compatibility(self, alice, bob):
        top_genres = alice.get_top_genres()
        sum = 0
        for track_id, track_info in bob.tracks.items():
            sum += alice.calc_track_match_probability(track_id, track_info, top_genres)
        if (len(bob.tracks) == 0):
            return 0
        return sum/len(bob.tracks)

    def common_tracks_playlist(self):
        all_tracks = copy.copy(self.user1.tracks)
        for k, v in self.user2.tracks.items():
            all_tracks[k] = v
        fav_genres1 = self.user1.get_top_genres()
        fav_genres2 = self.user2.get_top_genres()
        common_tracks = dict()
        for track_id, track_info in all_tracks.items():
            if (self.user1.calc_track_match_probability(track_id, track_info, fav_genres1) >= 0.6 and
                self.user2.calc_track_match_probability(track_id, track_info, fav_genres2) >= 0.6):
                common_tracks[track_id] = track_info
        playlist = list(common_tracks.items())
        random.shuffle(playlist)
        return dict(playlist[:min(20, len(playlist))])
      
      
# telegram-bot part

bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, f'Привет, {message.from_user.first_name}!\n'
                          f'Пока я умею делать две вещи: \n'
                          f'1. Выдавать анализ фонотеки пользователя Яндекс.Музыки -- для этого вызовите команду /analyse\n'
                          f'2. Определять совместимость двух пользователей Яндекс.Музыки по их музыкальным вкусам, '
                          f'основываясь на их любимых треках, -- для этого вызовите /match\n')


@bot.message_handler(commands=['analyse'])
def analyse(message):
    bot.reply_to(message,
                 'Введите имя пользователя Яндекс.Музыки, фонотеку которого хотите проанализировать.')


@bot.message_handler(commands=['match'])
def match(message):
    bot.reply_to(message, 'Через пробел введите имена двух пользователей Яндекс.Музыки, '
                          'чтобы посчитать их музыкальную совместимость.')


@bot.message_handler(content_types=['text'])
def get_text_message(message):
    text = message.text.strip()
    if (' ' in text):
        user_ids = text.split(' ')
        if (len(user_ids) > 2):
            bot.reply_to(message, 'Oops, вы ввели что-то не то, попробуйте снова.')
            return
        else:
            return twoUsersMatch(message, user_ids[0], user_ids[1])
    return userDataAnalysis(message, text)


def userDataAnalysis(message, user_id):
    bot.send_message(message.chat.id,
                     'Считаю... Это может занять пару минут, особенно если этот пользователь очень любит музыку :)')
    try:
        user = UserMusicData.from_url(user_id)
    except:
        bot.send_message(message.chat.id,
                         'Oops, что-то пошло не так. Вероятно, вы ввели некорректное имя пользователя. Попробуйте снова.\n')
        return
    if (len(user.tracks) == 0):
        bot.send_message(message.chat.id, 'У этого пользователя совсем пустая фонотека(')
        return
    bot.send_message(message.chat.id, 'Любимый исполнитель пользователя ' + user_id + ': ' + user.get_fav_artist() + '\n')
    try:
        img = open(user.get_genre_pie_image(), 'rb')
        bot.send_message(message.chat.id, 'Любимые жанры пользователя ' + user_id + ': \n')
        bot.send_photo(message.chat.id, img)
    except:
        bot.send_message(message.chat.id,
                         'Что-то пошло не так и мы не справились составить для вас диаграмму любимых жанров этого пользователя :( \n')


def playlist_dict_to_str(playlist) -> str:
    songs = ''
    i = 1
    for track_id, track_info in playlist.items():
        songs += str(i) + '. '
        songs += track_info.get('artist_name') + ' - ' + track_info.get('name') + '\n'
        i += 1
    return songs


def artists_dict_to_str(artists_dict) -> str:
    artists = ''
    i = 1
    for artist_id, artist_info in artists_dict.items():
        artists += str(i) + '. '
        artists += artist_info.get('name') + '\n'
        i += 1
    return artists


def twoUsersMatch(message, user1_id, user2_id):
    bot.send_message(message.chat.id,
                     'Считаю... Это может занять пару минут, особенно если эти пользователи очень любят музыку :)')
    try:
        user1 = UserMusicData.from_url(user1_id)
        print(user1.tracks)
        bot.send_message(message.chat.id,
                         'Еще чуть-чуть...')
        user2 = UserMusicData.from_url(user2_id)
        print(user2.tracks)
    except:
        bot.send_message(message.chat.id, 'Oops, что-то пошло не так. Вероятно, вы ввели некорректные имена пользователей. Попробуйте снова.\n')
        return
    users = UsersMatch(user1, user2)
    bot.send_message(message.chat.id, 'Музыкальная совместимость пользователей ' + user1_id + ' и ' + user2_id +
                                      ' составляет ' + str(round(users.calc_compatibility(user1, user2) * 100, 2)) + '%\n')

    artists_intersection = users.precise_artist_intersection()
    if (len(artists_intersection) != 0):
        artists_intersection_list = list(artists_intersection.items())
        random.shuffle(artists_intersection_list)
        artists_intersection = dict(artists_intersection_list[:min(10, len(artists_intersection_list))])
        artists = artists_dict_to_str(artists_intersection)
        bot.send_message(message.chat.id,
                         'Кажется, оба этих пользователя любят музыку следующих исполнителей:\n\n' + artists)

    tracks_intersection = users.precise_track_intersection()
    if (len(tracks_intersection) != 0):
        tracks_intersection_list = list(tracks_intersection.items())
        random.shuffle(tracks_intersection_list)
        tracks_intersection = dict(tracks_intersection_list[:min(10, len(tracks_intersection_list))])
        songs = playlist_dict_to_str(tracks_intersection)
        bot.send_message(message.chat.id,
                         'Ого! У этих пользователей есть общие любимые треки:\n\n' + songs)

    playlist = users.common_tracks_playlist()
    if (len(playlist) > 0):
      songs = playlist_dict_to_str(playlist)
      bot.send_message(message.chat.id,
                       'Составила плейлист с треками, которые могут понравиться как ' + user1_id + ', так и ' + user2_id + ': \n\n' + songs)

bot.polling(none_stop=True)
