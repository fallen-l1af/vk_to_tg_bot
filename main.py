#!/usr/lib/python3 python
# -*- coding: utf-8 -*-
import sys
import config
import telebot
from telebot import types as telebot_types
import vk
import time
import pprint
from telethon import TelegramClient, sync		# Do not delete sync, we need it to upload files
from tqdm import tqdm
import re
import os
import m3u8
import requests
from Crypto.Cipher import AES					# Crypto is pycryptodome
from Crypto.Util.Padding import unpad
import yt_dlp

config.initConfig()

module = sys.modules[__name__]


####################################################################################################
####							Read code from bottom to top									####
####################################################################################################

def get_updates():
	URL = f"https://api.telegram.org/bot{config.getCell('telegram_token')}/getUpdates"
	response = requests.get(URL)
	return response.json()

####################################################################################################

def find_next_filename(directory, name, file_extension):

	pattern = re.compile(rf"^{re.escape(name)}_(\d+)\.{re.escape(file_extension)}$")

	max_number = -1

	for filename in os.listdir(directory):
		match = pattern.match(filename)
		if match:
			number = int(match.group(1))
			if number > max_number:
				max_number = number

	if max_number == -1:
		return f"{name}_0.{file_extension}"
	else:
		return f"{name}_{max_number + 1}.{file_extension}"

def progress(current, total):
	global pbar
	global last_current
	if not (pbar):
		pbar = tqdm(total=total, desc=f"Uploading video")
	pbar.update(current - last_current)
	last_current = current

def get_last_file_id(type):
	updates = get_updates()
	file_id = 0
	if updates["result"]:
		message = updates["result"][-1]["message"]
		file_id = message[f"{type}"]["file_id"]
	return file_id

class M3U8Downloader:

	def __init__(self):
		pass

	def download_audio(self, url: str, name: str):

		if os.getcwd() != config.getCell("download_directory_path"):
			os.chdir(config.getCell("download_directory_path"))

		segments = self._get_audio_segments(url=url)
		segments_data = self._parse_segments(segments=segments)
		segments = self._download_segments(segments_data=segments_data, index_url=url)
		audio_name = self._convert_ts_to_mp3(segments=segments, name=name)

		return audio_name

	@staticmethod
	def _convert_ts_to_mp3(segments: bytes, name:str):
		name_1 = name
		name_parts = re.split(r" l__l ", name_1)
		artist = name_parts[0]
		title = name_parts[1]
		album = name_parts[2]

		name = 'audio'
		file_extension = 'mp3'
		audio_name = find_next_filename(config.getCell("download_directory_path"), name, file_extension)

		with open(config.getCell("download_directory_path") + 'temp.ts', 'w+b') as f:
			f.write(segments)
		os.system('ffmpeg -i '+ config.getCell("download_directory_path") +'temp.ts -metadata title="'+ title +'" -metadata artist="'+ artist +'" -metadata album="'+ album +'" "'+ config.getCell("download_directory_path") + audio_name +'"')
		# Here we use command line app ffmpeg to convert file from .ts to .mp3 and to add metadata
		os.remove(config.getCell("download_directory_path") + "temp.ts")

		return audio_name

	@staticmethod
	def _get_audio_segments(url: str):
		m3u8_data = m3u8.load(
			uri=url,
			verify_ssl=False
		)
		return m3u8_data.data.get("segments")

	@staticmethod
	def _parse_segments(segments: list):
		segments_data = {}

		for segment in segments:
			segment_uri = segment.get("uri")

			extended_segment = {
				"segment_method": None,
				"method_uri": None
			}
			if segment.get("key").get("method") == "AES-128":
				extended_segment["segment_method"] = True
				extended_segment["method_uri"] = segment.get("key").get("uri")
			segments_data[segment_uri] = extended_segment
		return segments_data

	@staticmethod
	def download_key(key_uri) -> bin:
		return requests.get(key_uri).content

	def _download_segments(self, segments_data: dict, index_url: str) -> bin:
		downloaded_segments = []

		for uri in segments_data.keys():
			audio = requests.get(url=index_url.replace("index.m3u8", uri))

			downloaded_segments.append(audio.content)

			if segments_data.get(uri).get("segment_method") is not None:
				key_uri = segments_data.get(uri).get("method_uri")
				key = self.download_key(key_uri)

				iv = downloaded_segments[-1][0:16]
				ciphered_data = downloaded_segments[-1][16:]

				cipher = AES.new(key, AES.MODE_CBC, iv=iv)
				data = unpad(cipher.decrypt(ciphered_data), AES.block_size)
				downloaded_segments[-1] = data

		return b''.join(downloaded_segments)

def start_pbar():
	global pbar
	global last_current
	pbar = False
	last_current = 0

def close_pbar():
	global pbar
	pbar.close
	pbar = False

####################################################################################################

def download_text_file(url, title):
	res = requests.get(url=url)
	with open(config.getCell("download_directory_path") + title, 'wb') as f:
		f.write(res.content)

def download_video(video_url):
	name = 'video'
	file_extension = 'mp4'
	video_name = find_next_filename(config.getCell("download_directory_path"), name, file_extension)
	video_path = config.getCell("download_directory_path") + video_name
	try:
		ydl_opts = {'outtmpl': video_path, 'quiet': True}
		with yt_dlp.YoutubeDL(ydl_opts) as ydl:
			ydl.download([video_url])
		return video_name
	except:
		print("Problem with video downloading")
		return ''

def upload_file(file, file_type):
	# We can upload files up to 2 gb only by using client api, not bot api
	client = TelegramClient(
		config.getCell("session_name"),
		config.getCell("api_id"),
		config.getCell("api_hash")
	)
	client.start()

	start_pbar()		# Initializing progress bar to track downloading process

	client.send_file(
		entity=config.getCell("bot_name"),
		file=file,
		use_cache=False,
		part_size_kb=1024,
		progress_callback=progress		# Function that updates progress bar
	)

	close_pbar()
	client.disconnect()

	file_id = get_last_file_id(file_type)
	# I don't know how to look up for all files sent from all users to telegram bot to be able to find
	# the specific file that WE sent, so I assume that everyone creates their own bot and hope
	# that it is true, and we can just take last file that our bot recieved
	return file_id

def process_doc_text_attachment(link, text, caption):
	
	global downloaded_files		# To be able to use and close files in other functions
	url = link
	title = text
	download_text_file(url, title)
	downloaded_text_path = config.getCell("download_directory_path") + title
	document_file = open(downloaded_text_path, 'rb')
	if os.path.getsize(downloaded_text_path) >= 50 * 1024 * 1024:
		# If file weights more than 50 mb, we can't upload it with bot api, so have to use client api
		file_id = upload_file(document_file, 'document')
		tg_attachment = telebot_types.InputMediaDocument(media=file_id, caption=caption)
	else:
		tg_attachment = telebot_types.InputMediaDocument(media=document_file, caption=caption)
	downloaded_files.append(document_file)
	
	return tg_attachment

def process_video_attachment(link, text, caption):

	global downloaded_files		# To be able to use and close files in other functions
	tg_attachment = None

	downloaded_video_name = download_video(link)
	downloaded_video_path = config.getCell("download_directory_path") + downloaded_video_name

	if os.path.isfile(downloaded_video_path):
		video_file = open(downloaded_video_path, 'rb')
		if os.path.getsize(downloaded_video_path) >= 50 * 1024 * 1024:
			# If file weights more than 50 mb, we can't upload it with bot api and have to use client api
			file_id = upload_file(video_file, 'video')
			tg_attachment = telebot_types.InputMediaVideo(media=file_id, caption=caption, supports_streaming=True)
		else:
			tg_attachment = telebot_types.InputMediaVideo(media=video_file, caption=caption, supports_streaming=True)
		downloaded_files.append(video_file)
	
	return tg_attachment

def process_audio_attachment(link, text, caption):

	global downloaded_files		# To be able to use and close files in other functions
	music_name = text
	md = M3U8Downloader() 		# Downloading music was uneasy, I stole and a litttle changed class M3U8Downloader
								# from someone other's github project, there is a link in file links.txt
	downloaded_audio_name = md.download_audio(link, music_name)
	downloaded_audio_path = config.getCell("download_directory_path") + downloaded_audio_name
	audio_file = open(downloaded_audio_path, 'rb')

	if os.path.getsize(downloaded_audio_path) >= 50 * 1024 * 1024:
		# If file weights more than 50 mb, we can't upload it with bot api, so we have to use client api
		file_id = upload_file(audio_file, 'document')
		tg_attachment = telebot_types.InputMediaAudio(media=file_id, caption=caption)
	else:
		tg_attachment = telebot_types.InputMediaAudio(media=audio_file, caption=caption)
	downloaded_files.append(audio_file)
	
	return tg_attachment

def process_animation_attachment(link, text, caption):

	tg_attachment = None
	module.bot.send_animation(chat_id=config.getCell("tg_chat_id"), animation=link, caption=caption)
	time.sleep(config.getCell("waiting_time"))
	
	return tg_attachment

####################################################################################################

def attachment_to_tg_attachment(attachment, caption=''):

	type = attachment.get( 'type' )
	link = attachment.get( 'link' )
	text = attachment.get('text')

	tg_attachment = None
	global downloaded_files		# To be able to use and close files in other functions

	if (type == 'photo' or type == 'sticker') and link is not None: # paid stickers don't give links to their images
		tg_attachment = telebot_types.InputMediaPhoto(media=link, caption=caption)

	elif type == 'doc_photo':
		tg_attachment = telebot_types.InputMediaDocument(media=link, caption=caption)

	elif type == 'doc_text':
		tg_attachment = process_doc_text_attachment(link, text, caption)


	elif type == 'video':
		tg_attachment = process_video_attachment(link, text, caption)


	elif type == 'audio':
		tg_attachment = process_audio_attachment(link, text, caption)


	elif type == 'animation':
		tg_attachment = process_animation_attachment(link, text, caption)


	# There are other types of attachments, but I haven't been working with them

	return tg_attachment

def make_media_group(attachments_with_links, caption):
	global downloaded_files
	downloaded_files = []

	media_group_audio = []	# Telegram asks not to mix music with videos and pictures and with other types of attachments
	media_group_video_and_pictures = []
	media_group_others = []

	attachment = attachments_with_links.pop(0)	# Here we add caption to the first attachment because only this caption will be shown when we have several attachments
	if attachment.get('type') == 'audio':
		media_group_audio.append(attachment_to_tg_attachment(attachment, caption))
	elif attachment.get('type') in ['video', 'photo']:
		media_group_video_and_pictures.append(attachment_to_tg_attachment(attachment, caption))
	else:
		media_group_others.append(attachment_to_tg_attachment(attachment, caption))

	for attachment in attachments_with_links:	# Here we add other attachments
		if attachment.get('type') == 'audio':
			media_group_audio.append(attachment_to_tg_attachment(attachment))
		elif attachment.get('type') in ['video', 'photo']:
			media_group_video_and_pictures.append(attachment_to_tg_attachment(attachment))
		else:
			media_group_others.append(attachment_to_tg_attachment(attachment))

	return [media_group_video_and_pictures, media_group_audio, media_group_others]

def close_all_files():
	global downloaded_files
	for file in downloaded_files:
		file.close()
	downloaded_files = []

def delete_all_files_in_directory(directory):
	for filename in os.listdir(directory):
		file_path = os.path.join(directory, filename)

		if os.path.isfile(file_path):
			os.remove(file_path)

def process_doc_attType(attachment, attType = 'doc', attachment_link = None, text_for_caption = ''):
	
	docType = attachment.get('type')	# Documentation about document types: https://vk.com/dev/objects/doc
	if docType in [6]:
		attType = 'video'
	elif docType in [3]:
		attType = 'animation'
		attachment_link = attachment.get('url')
	elif docType in [4]:  # photo
		attType = 'doc_photo'
		attachment = attachment.get('preview').get('photo')
		best_photo = attachment.get('sizes')[-1]
		attachment_link = best_photo.get('src')
	elif docType in [5]:
		attType = 'audio'
	elif docType in [1]:
		attType = 'doc_text'
		attachment_link = attachment.get('url')
		text_for_caption = attachment.get('title')
	
	return attType, attachment_link, text_for_caption

def process_sticker_attType(attachment, attachment_link = None):
	
	try:
		sticker_sizes = attachment.get('images')
		for sticker in sticker_sizes[0:]:
			if sticker.get('width') == 256:
				attachment_link = sticker.get('url')
	except:
		pass
	
	return attachment_link

def process_audio_attType(attachment):

	attachment_link = str(attachment.get('url'))
	artist = ''
	title = ''
	album = ''
	try:
		artist = attachment.get('artist')
	except:
		pass
	try:
		title = attachment.get('title')
	except:
		pass
	try:
		album = attachment.get('album').get('title')
	except:
		pass
	text_for_caption = artist + ' l__l ' + title + ' l__l ' + album
	
	return attachment_link, text_for_caption

def get_text_from_wall(attachment):

	group_id = abs(attachment.get('owner_id'))
	group_name = module.vk.groups.getById(group_id=group_id).get('groups')[0].get('name')
	wall_text = attachment.get('text')

	text_from_wall = (group_name + ' l__l ' + wall_text)
	
	return text_from_wall

def post_wall_history_attachments(attachment):

	try:
		wall_history_attachment = attachment.get('copy_history')
		if wall_history_attachment != None:
			for w_h_attachment in wall_history_attachment:
				wall_history_attachments = getVkAttachments(w_h_attachment.get('attachments'))
				post_media_group(wall_history_attachments)
	except:
		pass

def process_wall_reply_attType(attachment):

	attType = 'other'
	attachment_link = 'https://vk.com/wall'
	owner_id = str(attachment.get('owner_id'))
	reply_id = str(attachment.get('id'))
	post_id = str(attachment.get('post_id'))
	attachment_link += owner_id + '_' + post_id
	attachment_link += '?reply=' + reply_id
	
	return attType, attachment_link

def process_poll_attType(attachment):

	attType = 'other'
	attachment_link = 'https://vk.com/poll'
	owner_id = str(attachment.get('owner_id'))
	poll_id = str(attachment.get('id'))
	attachment_link += owner_id + '_' + poll_id
	
	return attType, attachment_link

####################################################################################################

def make_caption(recursion, sender_name, text):
	
	caption = ''
	if recursion > 1 or (recursion == 1 and sender_name != config.getCell("vk_name")) or text != '':
		caption = '-->' * max(recursion - 1, 0) + '| ' + sender_name + ' :   ' + text
	
	return caption

def add_text_from_wall_to_caption(caption, text_from_wall):
	
	wall_text_parts = re.split(r" l__l ", text_from_wall)
	group_name = ''
	wall_text = ''
	if config.getCell("vk_group_name"):
		group_name = wall_text_parts[0] + ' : '
	if config.getCell("vk_wall_caption"):
		wall_text = wall_text_parts[1]
	if group_name != '' or wall_text != '':
		if group_name != '' and wall_text != '':
			wall_caption = '| ' + group_name + '\n' + wall_text
		else:
			wall_caption = '| ' + group_name + wall_text
		if caption == '':
			caption = wall_caption
		else:
			caption += '\n\n' + wall_caption
	
	return caption


def post_media_group(attachments_with_links, caption=''):

	if attachments_with_links != None and attachments_with_links != []:
		media_group_list = make_media_group(attachments_with_links, caption)
		for media_group in media_group_list:
			media_group = [x for x in media_group if x is not None]
			if media_group != []:
				if media_group[0] != None:
					module.bot.send_media_group(chat_id=config.getCell("tg_chat_id"), media=media_group)
		close_all_files()	# We might have downloaded and opened several files, now we don't need them any more 
	delete_all_files_in_directory(config.getCell("download_directory_path"))

def getVkAttachments(attachments):
	attachList = []				# Here we put everything that we want to attach to a single message

	for att in attachments:
		attType = att.get('type')
		attachment = att[attType]
		
		attachment_link = None
		wall_attachments = []
		text_for_caption = ''

		if attType == 'doc':		# We work separately with docs to be able to process videos and audios not as docs further down in this function
			attType, attachment_link, text_for_caption = process_doc_attType(attachment)

		if attType == 'photo':
			best_photo = attachment.get('sizes')[-1]
			attachment_link = best_photo.get('url')

		elif attType == 'sticker':
			attachment_link = process_sticker_attType(attachment)

		elif attType == 'audio':
			attachment_link, text_for_caption = process_audio_attType(attachment)

		elif attType == 'audio_message':  	# Haven't tested
			attType = 'audio'
			attachment_link = attachment.get('link_ogg')

		elif attType == 'video':
			player = str(attachment.get('player'))
			attachment_link = player

		elif attType == 'graffiti':  		# Haven't tested
			attType = 'other'
			attachment_link = attachment.get('url')

		elif attType == 'link':  			# Haven't tested
			attType = 'other'
			attachment_link = attachment.get('url')

		elif attType == 'wall':
			wall_attachments = getVkAttachments(attachment.get('attachments'))
			text_from_wall = get_text_from_wall(attachment)
			
			post_wall_history_attachments(attachment)

		elif attType == 'wall_reply':		# Haven't tested
			attType, attachment_link = process_wall_reply_attType(attachment)

		elif attType == 'poll':  			# Haven't tested
			attType, attachment_link = process_poll_attType(attachment)

		if wall_attachments != []:			# We can attach a caption to a single attachment in a straight forward way, with several attachments we have to do some more complicated things 
			attachList = attachList + wall_attachments + [{'type': 'text_from_wall', 'text': text_from_wall}]
		elif attachment_link != None:
			attachList.append({'type': attType, 'link': attachment_link, 'text': text_for_caption})

	return attachList

####################################################################################################

def getVkUserName( from_id ):

	dataname = module.vk.users.get( v=config.getCell('v'), user_ids = from_id )
	name = str ( dataname[0]['first_name'] + ' ' + dataname[0]['last_name'] )
	return name

def send_text_and_attachments_from_vk_to_tg(recursion, sender_name, text, attachments):
	
	caption = make_caption(recursion, sender_name, text)
	
	if attachments == []:		# Checking if there is only text
		if caption != '':
			module.bot.send_message(config.getCell("tg_chat_id"), caption)
	else:
		attachments_with_links = getVkAttachments(attachments)

		if attachments_with_links[-1].get('type') == 'text_from_wall':
			# If attachment is some group's forwarded post, I keep this group's name and caption in
			# attachments_with_links[-1] and set its type as 'text_from_wall' - a unique type
			text_from_wall = attachments_with_links.pop().get('text')
			# Here I get rid of group's caption and stay with photos, audios, gifs and videos
			caption = add_text_from_wall_to_caption(caption, text_from_wall)

		post_media_group(attachments_with_links, caption)

	time.sleep(1)

def send_forwarded_and_reply_messages(recursion, forwarded_messages, reply_message):

	if forwarded_messages:
		new_recursion = recursion + 1
		for forwarded_message in forwarded_messages:
			time.sleep(config.getCell("waiting_time"))
			send_message_from_vk_to_tg(forwarded_message, new_recursion)

	if reply_message:
		new_recursion = recursion + 1
		time.sleep(config.getCell("waiting_time"))
		send_message_from_vk_to_tg(reply_message, new_recursion)

####################################################################################################

def get_last_forwarded_message_id():

	with open(config.getCell("project_directory_path") + "last_forwarded_message_id.txt", 'r') as f:
		last_forwarded_message_id = f.read()
	last_forwarded_message_id = int(last_forwarded_message_id)

	return last_forwarded_message_id

def get_last_message_id_in_chat():
    
	last_message_in_chat = module.vk.messages.getHistory(	access_token=config.getCell("access_token"),
																v=config.getCell('v'),
																start_message_id=-1,
																peer_id=config.getCell("peer_id"),
																count=1)
	last_message_id_in_chat = last_message_in_chat.get('items')[0].get('conversation_message_id')
	last_message_id_in_chat = int(last_message_id_in_chat)
	
	return last_message_id_in_chat
	
def get_new_messages_list(last_forwarded_message_id, last_id):
	
	rawMessages = module.vk.messages.getByConversationMessageId(
																access_token=config.getCell("access_token"),
																peer_id=config.getCell("peer_id"),
															conversation_message_ids=range(last_forwarded_message_id + 1, last_id + 1))
	new_messages_list = rawMessages.get('items')
	
	return new_messages_list

def update_last_forwarded_message_id(last_forwarded_message_id):
	
	last_forwarded_message_id += 1

	with open(config.getCell("project_directory_path") + "last_forwarded_message_id.txt", 'w') as f:
		f.write(str(last_forwarded_message_id))

	print(f'vk_sent {last_forwarded_message_id}')
	
	return last_forwarded_message_id

def send_message_from_vk_to_tg(message, recursion = 0):

	sender_name = getVkUserName(message.get('from_id'))
	text = message.get('text')
	attachments = message.get('attachments')
	forwarded_messages = message.get('fwd_messages')

	reply_message = message.get('reply_message')
	
	send_text_and_attachments_from_vk_to_tg(recursion, sender_name, text, attachments)
	send_forwarded_and_reply_messages(recursion, forwarded_messages, reply_message)

####################################################################################################

def initializing_in_vk_and_tg():

	module.vk= vk.API(access_token=config.getCell("access_token"), v=config.getCell('v'))
	print("logined in vk")

	module.bot = telebot.TeleBot(config.getCell('telegram_token'))
	print("logined in telegram")

def vk_listener():

	last_forwarded_message_id = get_last_forwarded_message_id()

	while True:

		last_message_id_in_chat = get_last_message_id_in_chat()

		if last_message_id_in_chat > last_forwarded_message_id:
			
			new_messages_list = get_new_messages_list(last_forwarded_message_id, last_message_id_in_chat)

			for message in new_messages_list:
				send_message_from_vk_to_tg(message)
				
				last_forwarded_message_id = update_last_forwarded_message_id(last_forwarded_message_id)
				
				time.sleep(config.getCell("waiting_time"))

		time.sleep(config.getCell("waiting_time"))

####################################################################################################

def main():
	initializing_in_vk_and_tg()
	vk_listener()

main()

####################################################################################################
