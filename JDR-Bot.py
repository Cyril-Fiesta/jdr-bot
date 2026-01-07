# JDR-Bot est mise à disposition selon les termes de la Licence Creative Commons Attribution - Partage dans les Mêmes
# Conditions 4.0 International. https://creativecommons.org/licenses/by-sa/4.0/
# Auteur : Cyril Meurier (Cyril-Fiesta) : http://www.cyril-fiesta.fr/  contact@cyril-fiesta.fr  https://discord.gg/Z63DtVV

import random
import asyncio
import aiohttp
import json
# import os  # A mettre si on veut tester un scénario en local.
import typing
import nextcord
import urllib.request
import re
import traceback
import sys
from bs4 import BeautifulSoup
import requests
import datetime
import time
from nextcord.ext.commands import Bot
from nextcord import Game
from nextcord.ext import commands
from nextcord.voice_client import VoiceClient
from nextcord.utils import get
from nextcord import FFmpegPCMAudio
from nextcord import Interaction
from copy import deepcopy

lang = {}
with open('lang.json', 'r') as f:
    lang = json.load(f)

with open('config.json', 'r') as f:  # token et id stocké sur un fichier externe
    config = json.load(f)

TOKEN = config['SECRET_TOKEN']  # Get at discordapp.com/developers/applications/me
My_ID = config['ID_DEV']  # mon id discord
BOT_NAME = config['BOT_NAME'] #Nom du bot avec tag
GUILD_TEST = config['GUILD_TEST'] #ID du serveur test
GUILD_OFF = config['GUILD_OFF'] #ID du serveur officiel

def charger_guilds(interaction):
    """Vérifie si l'id guild+salon a une langue définie et recharge le fichier lang.json."""
    global lang
    with open('lang.json', 'r') as f:
        lang = json.load(f)
        
    with open('guilds.json', 'r') as f: 
        guilds = json.load(f)
                
    if interaction.guild:    
        lang_id = "lang-" + str(interaction.channel_id) #vérifie et met une langue par défaut au channel actuel
        if lang_id not in guilds[str(interaction.guild_id)]:
            guilds[str(interaction.guild_id)][lang_id] = "fr"
        
        with open('guilds.json', 'w') as f: 
            json.dump(guilds, f, indent=4)
    
    return guilds

intents = nextcord.Intents.default()

bot = commands.Bot(command_prefix=commands.when_mentioned, case_insensitive=True, intents=intents)
bot.remove_command('help')

start_time = time.time()
categories_scenarios = {"📖": "fiction", "🔐": "escape-game", "👩‍🏫": "tutoriel", "🧩": "exemple", "🎮": "divers"}
url_certifiees = ("http://cyril-fiesta.fr/jdr-bot/scenarios/", "http://cyril-fiesta.fr/jdr-bot2/", "http://cyril-fiesta.fr/jdr-bot/scripts/")
jeu = {}
lien = {}


class Rpg:
    def __init__(self):
        self.markdown = ""
        self.inventaire_en_cours = []
        self.inventaire_invisible = []
        self.numero = []
        self.nom_salle = []
        self.texte = []
        self.objet = []
        self.case = []
        self.emplacement = 0
        self.emplacement_precedent = 0
        self.scenario = ""
        self.options = {}
        self.options_inv = {}
        self.description = {}
        self.variables = {"resultat": 0, "valeur": 0, "result": 0, "value": 0}
        self.variables_description = {"resultat": "Résultat de ... quelque chose !", 
                                      "valeur": "Valeur de ... quelque chose !", 
                                      "reponse": "Réponse à une question ...", 
                                      "action_cible": "dernière cible d'une action", 
                                      "action_cible_ok": "dernière cible existante d'une action",
                                      "result": "Result of ... something !", 
                                      "value": "Value of ... something !", 
                                      "answer": "Answer to a question...", 
                                      "action_target": "Last target of an action", 
                                      "action_target_ok": "Last correct target of an action"}
        self.variables_texte = {"action_cible": "null", "action_cible_ok": "null", 
                                "action_target": "null", "action_target_ok": "null"}
        self.action_custom = []
        self.nb_objets = []
        self.salle_react = []
        self.objetpr_react = []
        self.objetex_react = []
        self.meubleex_react = []
        self.event_react = []
        self.objet_reaction = {}  # Lie chaque reaction a l'objet correspondant
        self.salle_reaction = {}  # Lie chaque réaction à la salle correspondante
        self.alias_reaction = {}  # Lie chaque réaction à l'alias correspondant
        self.alias_reaction_inv = {}  # Dictionnaire alias/reaction inversé pour l'utilisation des réactions
        self.action_reaction = {}  # Lie chaque reaction à l'action correspndante
        self.action_reaction_inv = {}  # Lie chaque action à la reaction correspndante
        self.case_auto = 0
        self.variables_online = {}
        self.variables_texte_online = {}
        self.id_scenario = ""
        self.reaction_en_cours = 0
# jeu[id_partie].variable


class Url:
    def __init__(self):
        self.url_lien = []
        self.message_liste = None
        self.faq_on = None
        self.num_page = 0
        self.langue = "fr"
        self.categorie_actuel = "base"
# lien[id_partie].variable


@bot.event
async def on_ready():
    activite = "/help | JDR-Bot 3.1 ! " + str(len(bot.guilds)) + " serveurs."
    activity = nextcord.Game(name=activite)
    await bot.change_presence(activity=activity)
    servers_list = ""
    i = 0
    print("Logged in as " + bot.user.name)
    print("--- BOT ONLINE ---")
    
    with open('guilds.json', 'r') as f: 
        guilds = json.load(f)
    
    for element in guilds.keys():
        if "prefixes" in guilds[str(element)]:
            guilds[str(element)].pop("prefixes", None)
    
    for element in bot.guilds:
        if str(element.id) not in guilds:
            guilds[str(element.id)] = {}
            
        for channel in element.text_channels:
            if "jdr-bot" in str(channel):
                lang_id = "lang-" + str(channel.id)
                if lang_id not in guilds[str(element.id)]:
                    guilds[str(element.id)][lang_id] = "fr"
    
        with open('guilds.json', 'w') as f: 
            json.dump(guilds, f, indent=4)
        
        try:
            if i == 0:
                servers_list = element.name
                i = 1
            else:
                servers_list += " | " + element.name
        except:
            pass
    print('Active servers: ' + servers_list)


@bot.event
async def on_guild_join(guild):
    activite = "/help | JDR-Bot 3.1 ! " + str(len(bot.guilds)) + " serveurs."
    activity = nextcord.Game(name=activite)
    await bot.change_presence(activity=activity)
    with open('guilds.json', 'r') as f: 
        guilds = json.load(f)
    
    guilds[str(guild.id)] = {}
    
    for channel in guild.text_channels:
        if "jdr-bot" in str(channel):
            lang_id = "lang-" + str(channel.id)
            if lang_id not in guilds[str(guild.id)]:
                guilds[str(guild.id)][lang_id] = "fr"
    with open('guilds.json', 'w') as f: 
        json.dump(guilds, f, indent=4)


@bot.event
async def on_guild_remove(guild):
    activite = "/help | JDR-Bot 3.1 ! " + str(len(bot.guilds)) + " serveurs."
    activity = nextcord.Game(name=activite)
    await bot.change_presence(activity=activity)
    with open('guilds.json', 'r') as f: 
        guilds = json.load(f)
    
    guilds.pop(str(guild.id))
    
    with open('guilds.json', 'w') as f: 
        json.dump(guilds, f, indent=4)


@bot.event
async def on_guild_channel_create(channel):

    with open('guilds.json', 'r') as f: 
        guilds = json.load(f)

    lang_id = "lang-" + str(channel.id) #vérifie et met une langue par défaut au channel actuel
    if "jdr-bot" in str(channel) and lang_id not in guilds[str(channel.guild.id)]:
        guilds[str(channel.guild.id)][lang_id] = "fr"
    
    with open('guilds.json', 'w') as f: 
        json.dump(guilds, f, indent=4)
        
        
@bot.event
async def on_guild_channel_update(before,after):

    with open('guilds.json', 'r') as f: 
        guilds = json.load(f)

    lang_id = "lang-" + str(after.id) #vérifie et met une langue par défaut au channel actuel
    if "jdr-bot" in str(after) and lang_id not in guilds[str(after.guild.id)]:
        guilds[str(after.guild.id)][lang_id] = "fr"
    
    with open('guilds.json', 'w') as f: 
        json.dump(guilds, f, indent=4)


@bot.event
async def on_command_error(ctx, error):
    # This prevents any commands with local handlers being handled here in on_command_error.
    if hasattr(ctx.command, 'on_error'):
        return
    
    ignored = (commands.errors.UnexpectedQuoteError, commands.errors.ExpectedClosingQuoteError, commands.UserInputError, IndexError, KeyError, nextcord.errors.Forbidden, commands.CommandNotFound, commands.DisabledCommand)
        
    # Allows us to check for original exceptions raised and sent to CommandInvokeError.
    # If nothing is found. We keep the exception passed to on_command_error.
    error = getattr(error, 'original', error)
        
    # Anything in ignored will return and prevent anything happening.
    if isinstance(error, ignored):
        return

    else:
        print('Ignoring exception in command {}:'.format(ctx.message.content), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

@bot.event
async def on_error(event, *args, **kwargs):
    ignored = ("IndexError", "KeyError", "errors.Forbidden", "errors.NotFound")
    message = args[0] #Gets the message object
    if "interaction" in str(type(message)):
        try:
            await avoid_failed(message)
        except:
            pass
    if any(element in traceback.format_exc() for element in ignored):
        return
    else:
        print(traceback.format_exc()) #logs the error
        print(message)

async def avoid_failed(interaction: nextcord.Interaction):
    if interaction.response.is_done() is False:
        await interaction.send(".")
        msg = await interaction.original_message()
        await msg.delete()

@bot.slash_command()
async def ping(interaction: nextcord.Interaction):
    await interaction.send('Pong v2! `{0}ms`'.format(str(round(bot.latency, 3)*1000)[:3]))
    await avoid_failed(interaction)


async def warning_cmd(interaction: nextcord.Interaction, langue="fr", arg=""):  # Cette commande me permet de prevenir des maintenances, updates et restart du bot.
    """Réservée au developpeur du bot. Informe des maintenances, rédemarrages et mises à jour."""
    message = arg.replace('\n', '').replace('+n+', '\n')
    guilds = charger_guilds(interaction)
    if bot.user.avatar is None:
        avatar_bot = ""
    else:
        avatar_bot = bot.user.avatar.url
    if interaction.user.id == My_ID:   # mon id discord
        embed = nextcord.Embed(color=0x29d9e2, timestamp=datetime.datetime.utcnow())
        embed.set_author(name=bot.user.name+"#"+bot.user.discriminator, icon_url=avatar_bot)
        embed.set_thumbnail(url=avatar_bot)
        embed.add_field(name=f"Sent by {interaction.user}", value=message)
        await interaction.send("Transmission en cours !")
        for element in bot.guilds:
            for channel in element.text_channels:
                lang_id = "lang-"+str(channel.id)
                if "jdr-bot" in str(channel):
                    if lang_id in guilds[str(element.id)]:
                        langue_channel = guilds[str(element.id)]["lang-"+str(channel.id)]
                    else:
                        langue_channel = "fr"
                    if langue == langue_channel:
                        try:
                            await channel.send(embed=embed)
                            await asyncio.sleep(0.5)
                        except:
                            continue
    

@bot.slash_command(guild_ids=[GUILD_TEST,GUILD_OFF])
async def warning(interaction: nextcord.Interaction, langue: str, arg: str):
    await warning_cmd(interaction, langue, arg)
    await avoid_failed(interaction)


def charger_url(interaction):  # On charge les url de base et de la description.
    id_partie = str(interaction.guild_id)+str(interaction.channel_id)
    
    if id_partie not in lien:
        lien[id_partie] = Url()
    
    guilds = charger_guilds(interaction)
    if guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)] == "en":
        first_url = "http://cyril-fiesta.fr/jdr-bot/scripts/"
    else:
        first_url = "http://cyril-fiesta.fr/jdr-bot/scenarios/"
    
    if first_url not in lien[id_partie].url_lien:
        lien[id_partie].url_lien.append(first_url)
        
    try:
        topic = interaction.channel.topic.replace('\n', ' ').lower().split(" ")
        for element in topic:
            if element.startswith("http:"):
                url = element
                if url.endswith("/") is False:
                    url += "/"
                if url not in lien[id_partie].url_lien:
                    lien[id_partie].url_lien.append(url)
    except:
        pass


async def liens_scenarios_cmd(interaction: nextcord.Interaction, action="...", lien_scenarios="..."):
    """Affiche ou Modifie l'url où se trouve les scénarios."""
    id_partie = str(interaction.guild_id)+str(interaction.channel_id)
    charger_url(interaction)
    
    guilds = charger_guilds(interaction)
    lang_id = guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)]
    
    if "jdr-bot" not in interaction.channel.name:
        await interaction.send(f'```fix\n{lang[lang_id]["bad_channel"]}```')
        return
    
    if guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)] == "en":
        first_url = "http://cyril-fiesta.fr/jdr-bot/scripts/"
    else:
        first_url = "http://cyril-fiesta.fr/jdr-bot/scenarios/"
    
    lien_scenarios = lien_scenarios.lower()
    if lien_scenarios.endswith("/") is False:
        lien_scenarios += "/"
    perm_manage_channel = interaction.channel.permissions_for(interaction.user).manage_channels
    if action == "..." or action == "liste" or action == "list" or perm_manage_channel is False:
        liste_url = [lang[lang_id]["url_list"]]
        for element in lien[id_partie].url_lien:
            liste_url.append(str(element)+"\n")
        liste = ''.join(liste_url)
        await interaction.send(f'```fix\n{liste}```')
    elif action == "default" or action == "base" or action == "reset":
        lien[id_partie].url_lien = [first_url]
        await interaction.send(f'```fix\n{lang[lang_id]["url_new"]} {lien[id_partie].url_lien[0]}```')
    elif action == "add" or action == "ajouter":
        if lien_scenarios.startswith("http"):
            if lien_scenarios not in lien[id_partie].url_lien:
                lien[id_partie].url_lien.append(lien_scenarios)
                await interaction.send(f'```fix\n{lang[lang_id]["url_add"]}```')
            else:
                await interaction.send(f'```fix\n{lang[lang_id]["url_exist"]}```')
        else:
            await interaction.send(f'```fix\n{lang[lang_id]["url_incorrect"]}```')
    elif action == "retirer" or action == "remove":
        if lien_scenarios in lien[id_partie].url_lien:
            lien[id_partie].url_lien.remove(lien_scenarios)
            await interaction.send(f'```fix\n{lang[lang_id]["url_remove"]}```')
        else:
            await interaction.send(f'```fix\n{lang[lang_id]["url_missing"]}```')
    else:
        await interaction.send(f'```fix\n{lang[lang_id]["url_argument"]}```')

@bot.slash_command()
async def liens_scenarios(interaction: nextcord.Interaction, action: str = nextcord.SlashOption(required=False, default="..."), lien_scenarios: str = nextcord.SlashOption(required=False, default="...")):
    await liens_scenarios_cmd(interaction, action, lien_scenarios)
    await avoid_failed(interaction)
    
@bot.slash_command()
async def links(interaction: nextcord.Interaction, action: str = nextcord.SlashOption(required=False, default="..."), lien_scenarios: str = nextcord.SlashOption(required=False, default="...")):
    await liens_scenarios_cmd(interaction, action, lien_scenarios)
    await avoid_failed(interaction)

async def langue_cmd(interaction: nextcord.Interaction, langue="..."):
    """Affiche ou Modifie la langue du serveur."""
    guilds = charger_guilds(interaction)
    lang_id = guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)]
    charger_url(interaction)
    id_partie = str(interaction.guild_id)+str(interaction.channel_id)
    perm_manage_channel = interaction.channel.permissions_for(interaction.user).manage_channels
    langue = langue.lower()
    
    if "jdr-bot" not in interaction.channel.name:
        await interaction.send(f'```fix\n{lang[lang_id]["bad_channel"]}```')
        return
    
    if langue == "..." or langue == "liste" or langue == "list" or perm_manage_channel is False:
        await interaction.send(f'```{lang[lang_id]["lang_base"]} : {guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)]}```')
    elif langue == "fr" or langue == "en":
        guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)] = langue
        await interaction.send(f'```{lang[langue]["lang_change"]}```')
        if langue == "en":
            lien[id_partie].url_lien = ["http://cyril-fiesta.fr/jdr-bot/scripts/"]
        elif langue == "fr":
            lien[id_partie].url_lien = ["http://cyril-fiesta.fr/jdr-bot/scenarios/"]
    else:
        await interaction.send(f'```{lang[lang_id]["lang_unknown"]}```')
        
    with open('guilds.json', 'w') as f: 
        json.dump(guilds, f, indent=4)
    
@bot.slash_command()
async def lang(interaction: nextcord.Interaction, langue: str = nextcord.SlashOption(required=False, default="...")):
    await langue_cmd(interaction, langue)    
    await avoid_failed(interaction)

async def liste_scenarios_cmd(interaction: nextcord.Interaction, categorie = "base"):
    id_partie = str(interaction.guild_id)+str(interaction.channel_id)
    guilds = charger_guilds(interaction)
    lang_id = guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)]
        
    charger_url(interaction)
    view = categorieView()
    
    if "jdr-bot" not in interaction.channel.name:
        await interaction.send(f'```fix\n{lang[lang_id]["bad_channel"]}```')
        return
    
    for url in lien[id_partie].url_lien:
        liste_existante = 0
        try:
            page = requests.get(url).text
            i = 0
            nb_scenario = 0
            nb_page = 0
            soup = BeautifulSoup(page, 'html.parser')
            liste = [lang[lang_id]["list_scripts"], url, "\n"]
            for node in soup.find_all('a'):
                if node.get('href').endswith('.txt'):
                    liste.append(node.get('href')+"\n")
            for element in liste:
                if "liste_scenarios" in element:
                    liste_existante = 1
            if guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)] == "en":
                first_url = "http://cyril-fiesta.fr/jdr-bot/scripts/"
            else:
                first_url = "http://cyril-fiesta.fr/jdr-bot/scenarios/"
                
            categorie_title = categorie.lower()
            if guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)] == "en":
                if categorie == "tutorial" or categorie == "tutoriel":
                    categorie = "tutoriel"
                    categorie_title = "tutorial"
                elif categorie == "various" or categorie == "divers":
                    categorie = "divers"
                    categorie_title = "various"
                elif categorie == "example" or categorie == "exemple":
                    categorie = "exemple"
                    categorie_title = "example"
            
            if liste_existante == 1 and url == first_url:
                try:
                    liste_embed = urllib.request.urlopen(url+"liste_scenarios.txt").read().decode('utf-8')  # utf-8 pour remote files, ANSI pour locales files
                    liste_embed = liste_embed.split("\n")
                    if lien[id_partie].message_liste is None:
                        lien[id_partie].num_page = 0
                    if categorie.lower() in categories_scenarios.values():
                        categorie = categorie_title
                        if lien[id_partie].categorie_actuel != categorie.lower():
                            lien[id_partie].categorie_actuel = categorie.lower()
                            lien[id_partie].num_page = 0
                        for scenarios in liste_embed:
                            scenarios = scenarios.split("|")
                            if scenarios[1].lower() == categorie.lower():
                                nb_scenario += 1
                        nb_page = int(nb_scenario / 5)
                        if nb_scenario % 5 != 0:
                            nb_page += 1
                        if lien[id_partie].num_page > (nb_page - 1):
                            lien[id_partie].num_page = nb_page - 1
                            
                        embed = nextcord.Embed(color=0x256CB0, 
                                              title="" + categorie.capitalize() + " : "+ url, description="")
                        for scenarios in liste_embed:
                            scenarios = scenarios.split("|")
                            if scenarios[1].lower() == categorie.lower():
                                if i in range(lien[id_partie].num_page*5,lien[id_partie].num_page*5+5):
                                    texte = scenarios[0] + " "
                                    if scenarios[2].lower() == "yes":
                                        texte += " " + str("🏞️")
                                    if scenarios[3].lower() == "yes":
                                        texte += " " + str("🔊")
                                    if scenarios[4].lower() == "yes":
                                        texte += " " + str("🙂")
                                    embed.add_field(name=texte, value=scenarios[5], inline=False)
                                i += 1
                        embed.add_field(name="Page : " + str(lien[id_partie].num_page+1) + "/" + str(nb_page), value="\u23AF\u23AF\u23AF\u23AF\u23AF\u23AF\u23AF\u23AF\u23AF\u23AF\u23AF\u23AF\u23AF\u23AF", inline=False)
                        embed.add_field(name=lang[lang_id]["category_caption"][0], value=lang[lang_id]["category_caption"][1], inline=False)
                        embed.add_field(name=lang[lang_id]["list_category"][5], value=lang[lang_id]["list_category_full"], inline=False)
                        if lien[id_partie].message_liste is None:
                            await interaction.send(embed=embed, view=view)
                            lien[id_partie].message_liste = await interaction.original_message()
                        else:
                            await lien[id_partie].message_liste.edit(embed=embed, view=view)
                    else:
                        lien[id_partie].categorie_actuel = "base"
                        lien[id_partie].num_page = 0
                        embed = nextcord.Embed(color=0x256CB0, title=lang[lang_id]["list_category"][7])
                        embed.add_field(name=lang[lang_id]["list_category"][0], value=lang[lang_id]["category_description"][0], inline=False)
                        embed.add_field(name=lang[lang_id]["list_category"][1], value=lang[lang_id]["category_description"][1], inline=False)
                        embed.add_field(name=lang[lang_id]["list_category"][2], value=lang[lang_id]["category_description"][2], inline=False)
                        embed.add_field(name=lang[lang_id]["list_category"][3], value=lang[lang_id]["category_description"][3], inline=False)
                        embed.add_field(name=lang[lang_id]["list_category"][4], value=lang[lang_id]["category_description"][4], inline=False)
                        embed.add_field(name=lang[lang_id]["list_category"][6], value=lang[lang_id]["category_description"][5] + "/" + lang[lang_id]["category_description"][6], inline=False)
                        
                        await interaction.send(embed=embed, view=view)
                        lien[id_partie].message_liste = await interaction.original_message()
                        
                except:
                    liste.remove("liste_scenarios.txt\n")
                    liste = ''.join(liste)
                    await interaction.send(f'```fix\n{liste}```')
            elif categorie.lower() not in categories_scenarios.values():
                liste = ''.join(liste)
                await interaction.send(f'```fix\n{liste}```')
        except:
            pass

@bot.slash_command()
async def liste_scenarios(interaction: nextcord.Interaction, categorie: str = nextcord.SlashOption(required=False, default="base")):
    await liste_scenarios_cmd(interaction,categorie)
    await avoid_failed(interaction)

@bot.slash_command()
async def scripts(interaction: nextcord.Interaction, categorie: str = nextcord.SlashOption(required=False, default="base")):
    await liste_scenarios_cmd(interaction,categorie)
    await avoid_failed(interaction)

def lire_variable(interaction: nextcord.Interaction, texte):  # remplace v_variable_v par la valeur de variable
    id_partie = str(interaction.guild_id)+str(interaction.channel_id)
    if jeu[id_partie].id_scenario.startswith(url_certifiees):
        with open('variables_online.json', 'r') as var_o:
            jeu[id_partie].variables_online = json.load(var_o)
    for element in jeu[id_partie].variables_online[jeu[id_partie].id_scenario]:
        if isinstance(jeu[id_partie].variables_online[jeu[id_partie].id_scenario][element], int):
            jeu[id_partie].variables[element] = jeu[id_partie].variables_online[jeu[id_partie].id_scenario][element]
        else:
            jeu[id_partie].variables_texte[element] = jeu[id_partie].variables_online[jeu[id_partie].id_scenario][element]
        
    texte = str(texte)
    for element in jeu[id_partie].variables.keys():
        texte = texte.replace('v_'+element+'_v', str(jeu[id_partie].variables[element]))
    for element_t in jeu[id_partie].variables_texte.keys():
        texte = texte.replace('t_'+element_t+'_t', str(jeu[id_partie].variables_texte[element_t]))
    return texte


async def envoyer_texte(interaction: nextcord.Interaction, texte, avec_reaction="..."):  # Convertit les liens images et sons dans le texte, ainsi que le formattage.
    """Envoyer le texte sur discord après avoir séparé les images et les sons"""
    id_partie = str(interaction.guild_id)+str(interaction.channel_id)
    message = None
    msg = None
    guilds = charger_guilds(interaction)
    if "[[REACTION]]" in texte:
        avec_reaction = "ok"
    texte = lire_variable(interaction, texte)
    texte = texte.replace("[[PREFIX]]", "/" )
    texte = texte.replace("[[INVENTAIRE]]", ", ".join(jeu[id_partie].inventaire_en_cours))
    texte = texte.replace("[[INVENTORY]]", ", ".join(jeu[id_partie].inventaire_en_cours))
    texte = texte.replace("[[REACTION]]", "")
    for numero in range(len(jeu[id_partie].texte)):
        texte = texte.replace("[[SALLE:"+str(numero+1)+"]]", lire_variable(interaction, jeu[id_partie].texte[numero]))
        texte = texte.replace("[[ROOM:"+str(numero+1)+"]]", lire_variable(interaction, jeu[id_partie].texte[numero]))
    texte = texte.replace("[[", "|-*[[")
    texte = texte.replace("]]", "|-*")
    texte = texte.replace("<<", "|-*<<")
    texte = texte.replace(">>", "|-*")
    texte = texte.replace("{{", "|-*{{")
    texte = texte.replace("}}", "|-*")
    texte = texte.split('|-*')
    for element in texte:
        if element.startswith("[[") is True:  # afficher l'élément sans markdown
            element = element.replace("[[", "")
            if element != "":
                msg = await interaction.send(f'{element}')
                message = element
                if msg is None:
                    msg = await interaction.original_message()
        elif element.startswith("<<") is True:
            element = element.replace("<<", "")
            if element.lower().startswith("http"):
                voice = get(bot.voice_clients, guild=interaction.guild)
                try:
                    source = FFmpegPCMAudio(element, options='-loglevel quiet')  # On ignore les erreurs de conversation. Dans le pire des cas, ce son ne sera pas joué (mauvaise url, mauvais format, etc.)
                    if voice.is_playing():  # Si is_playing() is True => arrêt du son, puis diffusion du nouveau.
                        voice.stop()
                    voice.play(source)
                except:
                    pass
            elif element.lower() == "stop":
                voice = get(bot.voice_clients, guild=interaction.guild)
                if voice.is_playing():  # Si is_playing() is True => arrêt du son, puis diffusion du nouveau.
                    voice.stop()
            else:  # Si c'est pas un son, c'est un message TTS
                msg = await interaction.send(f'{element}')
                if msg is None:
                    msg = await interaction.original_message()
        elif element.startswith("{{") is True:
            element = element.replace("{{", "")
            try:
                await avoid_failed(interaction)
                await asyncio.sleep(int(element))
            except:
                pass
        elif element != "":
            if jeu[id_partie].markdown != "none\n" and jeu[id_partie].markdown != "null\n":
                element = "```" + str(jeu[id_partie].markdown) + element + "```"
            msg = await interaction.send(f'{element}')
            message = element
            if msg is None:
                msg = await interaction.original_message()
            
    test_precedent = 0  # On vérifie la présence de la direction "précédente" dans les direction de la case en cours
    for element in jeu[id_partie].case[jeu[id_partie].emplacement]:
        if "precedent" in element or "previous" in element:
            test_precedent = 1
            break
            
    if avec_reaction == "ok":
        try:  # au cas où il n'y a pas d'options à selectionner, le bot peut ignoré
            view = choixView(interaction)

            if message is None:
                await interaction.send(f'...',view=view)
            else:
                await msg.edit(view=view)
        except:
            pass
            
        
async def verifier_objets(interaction: nextcord.Interaction):  # Verifie les objets, variables et conditions présents dans une salle
    id_partie = str(interaction.guild_id)+str(interaction.channel_id)
    guilds = charger_guilds(interaction)
    lang_id = guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)]
    changement = 0
    if jeu[id_partie].objet[jeu[id_partie].emplacement][0] != "|":
        for o in range(jeu[id_partie].nb_objets[jeu[id_partie].emplacement]):
            cible_verifie = jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)]
            if jeu[id_partie].objet[jeu[id_partie].emplacement][1+(o*5)] == "invisible":
                jeu[id_partie].description[cible_verifie] = jeu[id_partie].objet[jeu[id_partie].emplacement][4+(o*5)]
                if cible_verifie[0] != "-" and cible_verifie not in jeu[id_partie].inventaire_invisible:
                    jeu[id_partie].inventaire_invisible.append(cible_verifie)
                    changement = 1
                elif cible_verifie[0] == "-":
                    if cible_verifie[1:] in jeu[id_partie].inventaire_invisible:
                        jeu[id_partie].inventaire_invisible.remove(cible_verifie[1:])
                        changement = 1
                    elif cible_verifie[1:] in jeu[id_partie].inventaire_en_cours:
                        jeu[id_partie].inventaire_en_cours.remove(cible_verifie[1:])
                        changement = 1
                        
            elif jeu[id_partie].objet[jeu[id_partie].emplacement][1+(o*5)] == "variable":
                jeu[id_partie].variables_description[cible_verifie] = lire_variable(interaction, jeu[id_partie].objet[jeu[id_partie].emplacement][4+(o*5)])
                try:
                    valeur_temp = jeu[id_partie].objet[jeu[id_partie].emplacement][2+(o*5)]
                    if valeur_temp[0] == "%" and valeur_temp[1] != "%":
                        valeur = lire_variable(interaction, valeur_temp[2:])
                        valeur = valeur.split(":")
                        valeur = valeur_temp[1] + str(random.randint(int(valeur[0]), int(valeur[1])))
                        jeu[id_partie].variables["resultat"] = valeur[1:]
                        jeu[id_partie].variables["result"] = valeur[1:]
                    else:
                        valeur = lire_variable(interaction, valeur_temp)
                    if valeur[0] == "=":
                        jeu[id_partie].variables[cible_verifie] = int(valeur[1:])
                    elif valeur[0] == "+":
                        jeu[id_partie].variables[cible_verifie] += int(valeur[1:])
                    elif valeur[0] == "-":
                        jeu[id_partie].variables[cible_verifie] -= int(valeur[1:])
                    elif valeur[0] == "/" and valeur[1] != "/":
                        jeu[id_partie].variables[cible_verifie] = int(round(jeu[id_partie].variables[cible_verifie] / int(valeur[1:])))
                    elif valeur[0] == "/" and valeur[1] == "/":
                        jeu[id_partie].variables[cible_verifie] = int(jeu[id_partie].variables[cible_verifie] / int(valeur[2:]))
                    elif valeur[0] == "*" and valeur[1] != "*":
                        jeu[id_partie].variables[cible_verifie] *= int(valeur[1:])
                    elif valeur[0] == "*" and valeur[1] == "*":
                        jeu[id_partie].variables[cible_verifie] **= int(valeur[2:])
                    elif valeur[0] == "%" and valeur[1] == "%":
                        jeu[id_partie].variables[cible_verifie] %= int(valeur[1:])
                    changement = 1
                    
                    if cible_verifie.endswith("_o"):
                        if jeu[id_partie].id_scenario.startswith(url_certifiees):  # si c'est une variable_o
                            jeu[id_partie].variables_online[jeu[id_partie].id_scenario][cible_verifie] = jeu[id_partie].variables[cible_verifie]
                            with open('variables_online.json', 'w') as var_o:
                                json.dump(jeu[id_partie].variables_online, var_o, indent=4)
                        
                except:
                    await interaction.send(f'```fix\n{lang[lang_id]["error001-1"]} {cible_verifie} {lang[lang_id]["error001-2"]} {lire_variable(interaction, jeu[id_partie].objet[jeu[id_partie].emplacement][2+(o*5)])}```')
                    
            elif jeu[id_partie].objet[jeu[id_partie].emplacement][1+(o*5)] == "variable_t":
                jeu[id_partie].variables_texte[jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)]] = lire_variable(interaction, jeu[id_partie].objet[jeu[id_partie].emplacement][2+(o*5)])
                jeu[id_partie].variables_description[jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)]] = lire_variable(interaction, jeu[id_partie].objet[jeu[id_partie].emplacement][4+(o*5)])
                
                if jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)].endswith("_o"):
                    if jeu[id_partie].id_scenario.startswith(url_certifiees):  # si c'est une variable_o
                        jeu[id_partie].variables_online[jeu[id_partie].id_scenario][jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)]] = jeu[id_partie].variables_texte[jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)]]
                        with open('variables_online.json', 'w') as var_o:
                            json.dump(jeu[id_partie].variables_online, var_o, indent=4)
                                
            if jeu[id_partie].objet[jeu[id_partie].emplacement][1+(o*5)] == "invisible" or jeu[id_partie].objet[jeu[id_partie].emplacement][1+(o*5)] == "variable":
                if jeu[id_partie].objet[jeu[id_partie].emplacement][3+(o*5)] != "null" and changement == 1:
                    await envoyer_texte(interaction, jeu[id_partie].objet[jeu[id_partie].emplacement][3+(o*5)])


async def condition_acces(interaction: nextcord.Interaction, case_actuelle, code="0"):  # Vérifie si les conditions d'accès à une salle sont respectées
    id_partie = str(interaction.guild_id)+str(interaction.channel_id)
    guilds = charger_guilds(interaction)
    lang_id = guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)]
    test = 2
    for objet_test in case_actuelle:  # on vérifie pour chaque objet requis et code
        try:  # On test si l'objet est un code, sinon ValueError, et si oui on test le code
            if int(objet_test) != int(code):
                test = 2
                break
            else:
                test = 1
        except ValueError:  # c'est donc un objet (texte) ou une variable, on regarde s'il est dans l'inventaire
            if objet_test == "null" or objet_test == "":
                test = 1
                break
            elif "§" in objet_test:  # si c'est une reaction, on ignore cette condition
                test = 1
            elif objet_test[0] == "$":
                test = 1
            elif objet_test[0] == '-':
                if objet_test[1:] in jeu[id_partie].inventaire_en_cours or objet_test[1:] in jeu[id_partie].inventaire_invisible:
                    test = 2
                    break
                else:
                    test = 1
            elif "." in objet_test:  # A partir de là, vérifier si c'est une variable.[operateur].valeur (donc si y'a un ".")
                try:  # Au cas où la variable indiqué n'existe pas, dù à une erreur dans le scénario
                    objet_test = objet_test.split(".")  # objet_test[0] = valeur/variable, [1] = opérateur, [2] = valeur/variable
                    if (objet_test[0].startswith("v_") or objet_test[2].startswith("v_")) and not (objet_test[0].startswith("t_") or objet_test[2].startswith("t_")):
                        if objet_test[1] == ">":
                            if int(lire_variable(interaction, objet_test[0])) > int(lire_variable(interaction, objet_test[2])):
                                test = 1
                            else:
                                test = 2
                                break
                        elif objet_test[1] == "<":
                            if int(lire_variable(interaction, objet_test[0])) < int(lire_variable(interaction, objet_test[2])):
                                test = 1
                            else:
                                test = 2
                                break
                        elif objet_test[1] == "=":
                            if int(lire_variable(interaction, objet_test[0])) == int(lire_variable(interaction, objet_test[2])):
                                test = 1
                            else:
                                test = 2
                                break
                        elif objet_test[1] == "<=":
                            if int(lire_variable(interaction, objet_test[0])) <= int(lire_variable(interaction, objet_test[2])):
                                test = 1
                            else:
                                test = 2
                                break
                        elif objet_test[1] == ">=":
                            if int(lire_variable(interaction, objet_test[0])) >= int(lire_variable(interaction, objet_test[2])):
                                test = 1
                            else:
                                test = 2
                                break
                        elif objet_test[1] == "!=":
                            if int(lire_variable(interaction, objet_test[0])) != int(lire_variable(interaction, objet_test[2])):
                                test = 1
                            else:
                                test = 2
                                break
                        elif objet_test[1] == "in":
                            limite = objet_test[2].split("-")
                            if int(lire_variable(interaction, objet_test[0])) in range(int(lire_variable(interaction, limite[0])), int(lire_variable(interaction, limite[1]))+1):
                                test = 1
                            else:
                                test = 2
                                break
                        elif objet_test[1] == "out":
                            limite = objet_test[2].split("-")
                            if int(lire_variable(interaction, objet_test[0])) not in range(int(lire_variable(interaction, limite[0])), int(lire_variable(interaction, limite[1]))+1):
                                test = 1
                            else:
                                test = 2
                                break
                        else:
                            test = 2
                            await interaction.send(f'```fix\n{".".join(objet_test)} {lang[lang_id]["incorrect_answer2"]}```')
                            break
                    elif objet_test[0].startswith("t_") or objet_test[2].startswith("t_"):
                        if objet_test[1] == "=":
                            if str(lire_variable(interaction, objet_test[0])) == str(lire_variable(interaction, objet_test[2])):
                                test = 1
                            else:
                                test = 2
                                break
                        elif objet_test[1] == "!=":
                            if str(lire_variable(interaction, objet_test[0])) != str(lire_variable(interaction, objet_test[2])):
                                test = 1
                            else:
                                test = 2
                                break
                        elif objet_test[1] == "in":
                            if str(lire_variable(interaction, objet_test[0])) in str(lire_variable(interaction, objet_test[2])):
                                test = 1
                            else:
                                test = 2
                                break
                        elif objet_test[1] == "out":
                            if str(lire_variable(interaction, objet_test[0])) not in str(lire_variable(interaction, objet_test[2])):
                                test = 1
                            else:
                                test = 2
                                break
                        else:
                            test = 2
                            await interaction.send(f'```fix\n{".".join(objet_test)} {lang[lang_id]["incorrect_answer2"]}```')
                            break
                except:
                    await interaction.send(f'```fix\n{lang[lang_id]["error_variable"]}```')
                    test = 2
                    break
            else:
                if objet_test not in jeu[id_partie].inventaire_en_cours and objet_test not in jeu[id_partie].inventaire_invisible:
                    test = 2
                    break
                else:
                    test = 1
    return test


async def executer_event(interaction: nextcord.Interaction, code="0", case_verifiee=None):
    if case_verifiee is None:
        case_verifiee = []
    id_partie = str(interaction.guild_id)+str(interaction.channel_id)
    guilds = charger_guilds(interaction)
    lang_id = guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)]
    nb_event = case_verifiee[2].split("@@")
    afficher_texte = 0
    for element in nb_event:
        try:
            if element.startswith("v_") and element.endswith("_v"):
                element = str(jeu[id_partie].variables[element[2:-2]])
                if int(element) < 1 or int(element) > len(jeu[id_partie].numero) or int(element) == (jeu[id_partie].emplacement+1):
                    element = "null"
            if element.isdigit():
                temporaire = case_verifiee[3]  # on garde de coté le texte de l'event si y'a pas d'erreur
                jeu[id_partie].emplacement_precedent = jeu[id_partie].emplacement
                jeu[id_partie].emplacement = int(element)-1
                if temporaire != "null":  # pas d'erreur (except) ni de texte null, on envoit
                    # if "[[REACTION]]" in temporaire:
                        # await envoyer_texte(interaction, temporaire, avec_reaction="ok")
                    # else:
                    await envoyer_texte(interaction, temporaire)
                if jeu[id_partie].texte[jeu[id_partie].emplacement] != "null":
                    await envoyer_texte(interaction, jeu[id_partie].texte[jeu[id_partie].emplacement], avec_reaction="ok")
                jeu[id_partie].case_auto += 1
                await verifier_objets(interaction)
                if jeu[id_partie].case_auto > 25:
                    return "break"
                await verifier_cases_speciales(interaction, code)
                return "break"
            elif element == "null":
                if case_verifiee[3] != "null":
                    afficher_texte = 1
            elif "&&" in element:
                try:
                    objet_temp = element.split("&&")

                    if objet_temp[1] == "inventaire" or objet_temp[1] == "inventory" :
                        jeu[id_partie].description[objet_temp[0]] = objet_temp[2]
                        if objet_temp[0][0] == "-" and objet_temp[0][1:] in jeu[id_partie].inventaire_en_cours:
                            jeu[id_partie].inventaire_en_cours.remove(objet_temp[0][1:])
                            if case_verifiee[3] != "null":
                                afficher_texte = 1
                        elif objet_temp[0][0] != "-" and objet_temp[0] not in jeu[id_partie].inventaire_en_cours:
                            jeu[id_partie].inventaire_en_cours.append(objet_temp[0])
                            if case_verifiee[3] != "null":
                                afficher_texte = 1
                        else:
                            pass  # s'il n'y a pas de changement, on ignore le 997, contrairement à !prendre qui affiche un texte
                    
                    elif objet_temp[1] == "invisible":
                        jeu[id_partie].description[objet_temp[0]] = objet_temp[2]
                        if objet_temp[0][0] == "-" and objet_temp[0][1:] in jeu[id_partie].inventaire_invisible:
                            jeu[id_partie].inventaire_invisible.remove(objet_temp[0][1:])
                            if case_verifiee[3] != "null":
                                afficher_texte = 1
                        elif objet_temp[0][0] != "-" and objet_temp[0] not in jeu[id_partie].inventaire_invisible:
                            jeu[id_partie].inventaire_invisible.append(objet_temp[0])
                            if case_verifiee[3] != "null":
                                afficher_texte = 1
                        else:
                            pass  # s'il n'y a pas de changement, on ignore le 997, contrairement à !prendre qui affiche un texte
                    
                    elif objet_temp[1] == "variable":
                        jeu[id_partie].variables[objet_temp[0]] = int(lire_variable(interaction, objet_temp[2]))
                        jeu[id_partie].variables_description[objet_temp[0]] = str(lire_variable(interaction, objet_temp[3]))
                        if case_verifiee[3] != "null":
                            afficher_texte = 1
                        if objet_temp[0].endswith("_o"):
                            if jeu[id_partie].id_scenario.startswith(url_certifiees):
                                jeu[id_partie].variables_online[jeu[id_partie].id_scenario][objet_temp[0]] = jeu[id_partie].variables[objet_temp[0]]
                                with open('variables_online.json', 'w') as var_o:
                                    json.dump(jeu[id_partie].variables_online, var_o, indent=4)
                    
                    elif objet_temp[1] == "variable_t":
                        jeu[id_partie].variables_texte[objet_temp[0]] = str(lire_variable(interaction, objet_temp[2]))
                        jeu[id_partie].variables_description[objet_temp[0]] = str(lire_variable(interaction, objet_temp[3]))
                        if case_verifiee[3] != "null":
                            afficher_texte = 1
                        if objet_temp[0].endswith("_o"):
                            if jeu[id_partie].id_scenario.startswith(url_certifiees):
                                jeu[id_partie].variables_online[jeu[id_partie].id_scenario][objet_temp[0]] = jeu[id_partie].variables_texte[objet_temp[0]]
                                with open('variables_online.json', 'w') as var_o:
                                    json.dump(jeu[id_partie].variables_online, var_o, indent=4)

                except:
                    pass
            elif "." in element:
                variable_modifiee = [""]
                try:
                    variable_modifiee = element.split(".")
                    if variable_modifiee[0].endswith("_o"):
                        if jeu[id_partie].id_scenario.startswith(url_certifiees):
                            with open('variables_online.json', 'r') as var_o:
                                jeu[id_partie].variables_online = json.load(var_o)
                            jeu[id_partie].variables[variable_modifiee[0]] = jeu[id_partie].variables_online[jeu[id_partie].id_scenario][variable_modifiee[0]]
                        
                    if not isinstance(variable_modifiee[2], int):
                        variable_modifiee[2] = lire_variable(interaction, variable_modifiee[2])
                    if variable_modifiee[0] not in jeu[id_partie].variables:
                        jeu[id_partie].variables[variable_modifiee[0]] = 0
                        jeu[id_partie].variables_description[variable_modifiee[0]] = "..."
                    if  variable_modifiee[2][0] == "%":
                        valeur = variable_modifiee[2][1:].split(":")
                        valeur = variable_modifiee[1] + str(random.randint(int(valeur[0]), int(valeur[1])))
                        jeu[id_partie].variables["resultat"] = valeur[1:]
                        jeu[id_partie].variables["result"] = valeur[1:]
                    else:
                        valeur = variable_modifiee[1] + variable_modifiee[2]
                    if valeur[0] == "=":
                        jeu[id_partie].variables[variable_modifiee[0]] = int(valeur[1:])
                    elif valeur[0] == "+":
                        jeu[id_partie].variables[variable_modifiee[0]] += int(valeur[1:])
                    elif valeur[0] == "-":
                        jeu[id_partie].variables[variable_modifiee[0]] -= int(valeur[1:])
                    elif valeur[0] == "/" and valeur[1] != "/":
                        jeu[id_partie].variables[variable_modifiee[0]] = int(round(jeu[id_partie].variables[variable_modifiee[0]] / int(valeur[1:])))
                    elif valeur[0] == "/" and valeur[1] == "/":
                        jeu[id_partie].variables[variable_modifiee[0]] = int(jeu[id_partie].variables[variable_modifiee[0]] / int(valeur[2:]))
                    elif valeur[0] == "*" and valeur[1] != "*":
                        jeu[id_partie].variables[variable_modifiee[0]] *= int(valeur[1:])
                    elif valeur[0] == "*" and valeur[1] == "*":
                        jeu[id_partie].variables[variable_modifiee[0]] **= int(valeur[2:])
                    elif valeur[0] == "%" and valeur[1] == "%":
                        jeu[id_partie].variables[variable_modifiee[0]] %= int(valeur[1:])
                    
                    if case_verifiee[3] != "null":
                        afficher_texte = 1
                    
                    if variable_modifiee[0].endswith("_o"):
                        if jeu[id_partie].id_scenario.startswith(url_certifiees):
                            jeu[id_partie].variables_online[jeu[id_partie].id_scenario][variable_modifiee[0]] = jeu[id_partie].variables[variable_modifiee[0]]
                            with open('variables_online.json', 'w') as var_o:
                                json.dump(jeu[id_partie].variables_online, var_o, indent=4)

                except:
                    await interaction.send(f'```fix\n{lang[lang_id]["error002-1"]} {variable_modifiee[0]} {lang[lang_id]["error002-2"]} {element}```')
        except IndexError:
            await interaction.send(f'```fix\n{lang[lang_id]["wrong_nb_rooms"]}```')
            return "break"
    if afficher_texte == 1:
        # if "[[REACTION]]" in case_verifiee[3]:  
            # await envoyer_texte(interaction, case_verifiee[3], avec_reaction="ok")
        # else:
        await envoyer_texte(interaction, case_verifiee[3])


async def verifier_cases_speciales(interaction: nextcord.Interaction, code="0"):
    id_partie = str(interaction.guild_id)+str(interaction.channel_id)
    for case_verifiee in jeu[id_partie].case[jeu[id_partie].emplacement]:
        if isinstance(case_verifiee, list) is False:
            pass
        elif case_verifiee[0] == "997":
            presence_reaction = 0
            for objet in case_verifiee[1]:
                if "§" in objet:
                    presence_reaction = 1
            if presence_reaction == 1:
                pass
            elif case_verifiee[1] == "null" or await condition_acces(interaction, case_verifiee[1], code) == 1:
                event = await executer_event(interaction, code, case_verifiee)
                if event == "break":
                    if id_partie in jeu:
                        jeu[id_partie].case_auto = 0
                    break
            else:
                pass
        elif case_verifiee[0] == "999" or case_verifiee[0] == "998":
            if case_verifiee[1] != "null":
                await envoyer_texte(interaction, case_verifiee[1])
            await asyncio.sleep(2)
            del jeu[id_partie]
            try:
                voice = get(bot.voice_clients, guild=interaction.guild)
                if voice.is_playing():
                    voice.stop()
                await voice.disconnect()
            except:
                pass
            return
        else:
            pass


@bot.slash_command()
async def jeter_des(interaction: nextcord.Interaction, choix_des: str):
    """j!jeter_des XdY' lance X dés de Y faces (1d6 par défaut)"""
    resultat = []
    reussite = 0
    total = 0
    nb_reussite_total = 0
    valeur_ajoutee = 0

    if choix_des == "":
        choix_des = "1d6"
    choix_des = choix_des.replace("D", "d")
    choix_des = choix_des.replace(" + ", "+")
    choix_des = choix_des.replace("+ ", "+")
    choix_des = choix_des.replace(" +", "+")
    choix_des = choix_des.replace(" ", "+")
    try:
        lancer_total = choix_des.split("+")
        for element in lancer_total:  # Pour chaque lancer dans la commande
            total_temp = 0
            reussite = 0
            nb_reussite = 0
            valeur_relance = 0
            valeur_ajout = 0
            if element.isdigit():  # si c'est une simple valeur, on l'ajoute
                total += int(element)
                valeur_ajoutee += int(element)
            else:  # Si c'est un lancer, on le décompose
                type_actuel = element.split("d")  # On sépare le nombre de dés et de faces
                nombre_des = int(type_actuel[0])  # D'abord le nombre de dés
                if nombre_des > 100:
                    nombre_des = 100
                pos1 = type_actuel[1].find("r")  # On determine si y'a un "r" et sa position => relance si valeur
                pos2 = type_actuel[1].find("m")  # On determine si y'a un "m" et sa position => ajoute un dé si dé = valeur
                pos3 = type_actuel[1].find("!")  # On determine si y'a un "!" et sa position => compte réussites si valeur >= X
                if pos1 > 0:  # Si y'a un "r", on recupère la valeur des dés à relancer
                    if pos2 > 0:
                        valeur_relance = int(type_actuel[1][pos1+1:pos2])
                    elif pos3 > 0:
                        valeur_relance = int(type_actuel[1][pos1+1:pos3])
                    else:
                        valeur_relance = int(type_actuel[1][pos1+1:])
                        
                if pos2 > 0:  # Si y'a un "m", on récupère la valeur pour laquelle on ajoute un dé
                    if pos3 > 0:
                        valeur_ajout = int(type_actuel[1][pos2+1:pos3])
                    else:
                        valeur_ajout = int(type_actuel[1][pos2+1:])
                        
                if pos3 > 0:  # si y'a un "!", on récupère la valeur à partir de laquelle on compte les réussites
                    reussite = int(type_actuel[1][pos3+1:])
                    
                if pos1 > 0:
                    nombre_face = int(type_actuel[1][:pos1])
                elif pos2 > 0:
                    nombre_face = int(type_actuel[1][:pos2])
                elif pos3 > 0:
                    nombre_face = int(type_actuel[1][:pos3])
                else:
                    nombre_face = int(type_actuel[1])
                if nombre_face > 10000:
                    nombre_face = 10000

                resultat.append("D"+str(nombre_face)+" : ")
                i = 0
                while i < int(nombre_des):
                    if valeur_relance > 0:
                        while True:  # Boucle qui se repete si le dé donne la valeur de relance
                            temp = random.randint(1, nombre_face)
                            if temp != valeur_relance:
                                break
                    else:
                        temp = random.randint(1, nombre_face)
                    if reussite > 0:
                        if temp >= reussite:
                            nb_reussite += 1
                    if temp != valeur_ajout or valeur_ajout <= 0:
                        i += 1
                    total_temp += temp
                    resultat.append(str(temp)+" ")
                resultat.append("(="+str(total_temp)+")")
                if reussite > 0:
                    resultat.append("(nombre de réussites : "+str(nb_reussite)+")\n")
                else:
                    resultat.append("\n")
                total += total_temp
                nb_reussite_total += nb_reussite
        resultat.append("total : "+str(total)+" (dés + "+str(valeur_ajoutee)+") ")
        if reussite > 0:
            resultat.append("(Nombre de réussites totales : "+str(nb_reussite_total)+")")
    except (ValueError, IndexError):
        await interaction.send(f'```fix\nErreur dans les paramètres. exemple : !jeter_des 2d6  pour 2 dés de 6 faces```')
    else:
        resultat = ''.join(map(str, resultat))
        await interaction.send(f'```{resultat}```')
    
    await avoid_failed(interaction)


async def lancer_pieces_cmd(interaction, nombre_piece = 1):
    """j!lancer_pieces X' lance X pièces (1 par défaut)"""
    resultat = []
    try:
        nombre_piece = int(nombre_piece)
        for i in range(nombre_piece):
            if random.randint(0, 1) == 0:
                resultat.append("pile")
            else:
                resultat.append("face")
            i += 1
    except:
        await interaction.send(f'```fix\nErreur dans les paramètres. !lancer_pieces[nombre de pièces]```')
    else:
        resultat = ', '.join(map(str, resultat))
        await interaction.send(f'```fix\nVous avez obtenu : {resultat}```')

@bot.slash_command(description="Lance X pièce(s) (1 par défaut)", )
async def lancer_pieces(interaction: nextcord.Interaction, nombre_pieces: int = nextcord.SlashOption(required=False, default=1)):
    await lancer_pieces_cmd(interaction, nombre_pieces)
    await avoid_failed(interaction)

@bot.slash_command()
async def coin(interaction: nextcord.Interaction, number_coins: int = nextcord.SlashOption(required=False, default=1)):
    """Throw X coin(s)(default = 1)"""
    await lancer_pieces_cmd(interaction, number_coins)
    await avoid_failed(interaction)


async def jouer_cmd(interaction: nextcord.Interaction, nom_scenario="..."):
    """j!jouer choix' lance une partie avec le scenario \"choix\""""
    id_partie = str(interaction.guild_id)+str(interaction.channel_id)
    guilds = charger_guilds(interaction)
    lang_id = guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)]
    
    if "jdr-bot" not in interaction.channel.name:
        await interaction.send(f'```fix\n{lang[lang_id]["bad_channel"]}```')
        return
    
    if id_partie in jeu:
        await interaction.send(f'```fix\n{lang[lang_id]["game_in_progress"]}```')
        return 0
    elif nom_scenario == "...": #and len(interaction.message.attachments) == 0:
        await interaction.send(f'```fix\n{lang[lang_id]["play_argument1"]}/{lang[lang_id]["play_argument2"]}```')
        return 0
    i = 0
    j = 2

    jeu[id_partie] = Rpg()
    # path = os.getcwd() + "\scenarios"  # pour test en local
    charger_url(interaction)
    try:  # ouvre le scénario
        # if interaction.message.attachments:
            # jeu[id_partie].scenario = await interaction.message.attachments[0].read()
            # jeu[id_partie].scenario = jeu[id_partie].scenario.decode("utf-8").splitlines()
            # jeu[id_partie].id_scenario = "discord/" + nom_scenario
        if nom_scenario.isdigit():
            jeu[id_partie].scenario = await interaction.channel.fetch_message(int(nom_scenario))
            jeu[id_partie].scenario = await jeu[id_partie].scenario.attachments[0].read()
            jeu[id_partie].scenario = jeu[id_partie].scenario.decode("utf-8").splitlines()
            jeu[id_partie].id_scenario = "discord/" + nom_scenario
        else:

            if nom_scenario.lower().endswith(".txt") is False and nom_scenario.lower().startswith("http") is False:
                nom_scenario += ".txt"
        
            # à partir d'un dossier local
            # with open(os.path.join(path, nom_scenario), 'r', encoding="utf8") as data:
                # jeu[id_partie].scenario = data.readlines()
            
            # à partir d'une url  
            url_actuelle = ""
            for url in lien[id_partie].url_lien:  # On vérifie si le scénario existe, url par url.
                try:
                    page = requests.get(url).text
                    soup = BeautifulSoup(page, 'html.parser')
                    liste = []
                    for node in soup.find_all('a'):
                        if node.get('href').endswith('.txt'):
                            liste.append(node.get('href'))
                    liste2 = [x.lower() for x in liste]
                    nom_scenario_l = nom_scenario.lower()
                    if nom_scenario_l in liste2:
                        url_actuelle = url
                        position = liste2.index(nom_scenario_l)
                        nom_scenario = liste[position]
                        break
                except:  # si l'url est incorrecte, on passera à la suivante
                    pass
            data = urllib.request.urlopen(url_actuelle+nom_scenario).read().decode('utf-8')  # utf-8 pour remote files, ANSI pour locales files
            data = data.replace("\n", "/n\n").split("\n")
            jeu[id_partie].scenario = [x.replace("/n", "\n") for x in data]
            
            jeu[id_partie].id_scenario = url_actuelle+nom_scenario  # Version en ligne
            # jeu[id_partie].id_scenario = "local/" + nom_scenario  # Version en local
        
    except:  # gérer l'erreur : le scénario n'a pas été trouvé sur une des url ou son nom est incorrect.
        await interaction.send(f'```fix\n{lang[lang_id]["unknown_script"]} "{nom_scenario}" !```')
        del jeu[id_partie]
        return
        
    try:
        voice = get(bot.voice_clients, guild=interaction.guild)
        try:
            channel = nextcord.utils.get(interaction.guild.voice_channels, name="JDR-Bot")
            voice = await channel.connect(timeout=3, reconnect=False)
        except asyncio.TimeoutError:
            await interaction.send(f'```fix\n{lang[lang_id]["cant_connect_vocal"]}```')
        except:
            await interaction.send(f'```fix\n{lang[lang_id]["cant_find_vocal"]}```')
        if jeu[id_partie].id_scenario.startswith(url_certifiees):
            with open('variables_online.json', 'r') as var_o:
                jeu[id_partie].variables_online = json.load(var_o)
        if jeu[id_partie].id_scenario not in jeu[id_partie].variables_online:
            jeu[id_partie].variables_online[jeu[id_partie].id_scenario] = {}
            
        if "nb_parties_o" in jeu[id_partie].variables_online[jeu[id_partie].id_scenario]:
            jeu[id_partie].variables_online[jeu[id_partie].id_scenario]["nb_parties_o"] += 1
            jeu[id_partie].variables["nb_parties_o"] = jeu[id_partie].variables_online[jeu[id_partie].id_scenario]["nb_parties_o"]
        else:
            jeu[id_partie].variables["nb_parties_o"] = 1
            jeu[id_partie].variables_online[jeu[id_partie].id_scenario]["nb_parties_o"] = 1
        jeu[id_partie].variables_description["nb_parties_o"] = "Nombre de parties jouées/Number of games played."
        
        if jeu[id_partie].id_scenario.startswith(url_certifiees):
            with open('variables_online.json', 'w') as var_o:
                json.dump(jeu[id_partie].variables_online, var_o, indent=4)

        jeu[id_partie].scenario = [ligne for ligne in jeu[id_partie].scenario if ligne != '\n' and ligne != '\r']
        tableau_tmp = []
        tmp = ""

        for ligne in jeu[id_partie].scenario:  # fusionne les lignes coupé par &&, et ignore les commentaires ("##")
            ligne = ligne.replace("\n", "")
            ligne = ligne.replace("\r", "")
            ligne = ligne.split("##")[0]
            if ligne.endswith("&&"):
                tmp += ligne[:-2]
            else:
                if tmp != "":
                    tableau_tmp.append(tmp + ligne)
                    tmp = ""
                else:
                    tableau_tmp.append(ligne)
        jeu[id_partie].scenario = tableau_tmp

        jeu[id_partie].scenario[0] = jeu[id_partie].scenario[0].replace('\n', "").replace('+n+', '\n')
        if "|" in jeu[id_partie].scenario[0]:
            temp = jeu[id_partie].scenario[0].split("|")
            elem = 0
            for element in temp:
                if elem == 0:
                    jeu[id_partie].scenario[0] = element
                    elem += 1
                elif "§" in element:
                    element = element.split("§")
                    jeu[id_partie].options[element[0]] = element[1]
                    jeu[id_partie].options_inv[element[1]] = element[0]

        jeu[id_partie].scenario[3] = jeu[id_partie].scenario[3].rstrip().replace('+n+', '\n')
        num_markdown = jeu[id_partie].scenario[1].split(" ")
        if len(num_markdown) > 1:
            nombre_max = int(num_markdown[0])
            jeu[id_partie].markdown = str(num_markdown[1])+"\n"
        else:
            nombre_max = int(num_markdown[0])
            jeu[id_partie].markdown = "fix\n"

        while i < nombre_max:  # Pour chaque case du scénario
            jeu[id_partie].scenario[i+j] = jeu[id_partie].scenario[i+j].split(" ",maxsplit=1)
            jeu[id_partie].numero.append(jeu[id_partie].scenario[i+j][0])
            jeu[id_partie].salle_reaction[str(int(jeu[id_partie].numero[i])-1)] = []
            if "§" in jeu[id_partie].scenario[i+j][1]:  # Si on a ajouter une reaction au nom de salle (avec le séparateur §)
                jeu[id_partie].scenario[i+j][1] = jeu[id_partie].scenario[i+j][1].split("§")  # on sépare nom et reaction
                jeu[id_partie].nom_salle.append(jeu[id_partie].scenario[i+j][1][0])  # on récupère le nom
                jeu[id_partie].salle_react.append(jeu[id_partie].scenario[i+j][1][1].replace('\n', ''))  # on récupère la réaction de salle
            else:
                jeu[id_partie].nom_salle.append(jeu[id_partie].scenario[i+j][1].replace('\n', ''))
                jeu[id_partie].salle_react.append("...")
            j += 1
            jeu[id_partie].texte.append(jeu[id_partie].scenario[i+j])
            jeu[id_partie].texte[i] = jeu[id_partie].texte[i].rstrip().replace('+n+', '\n')
            j += 1
            if jeu[id_partie].scenario[i+j].strip() == "|":
                jeu[id_partie].objet.append(jeu[id_partie].scenario[i+j].strip())
                jeu[id_partie].nb_objets.append(0)
            else:
                jeu[id_partie].objet.append(jeu[id_partie].scenario[i+j].strip().split("|"))
                jeu[id_partie].nb_objets.append(int(len(jeu[id_partie].objet[i])/5))
                for o in range(jeu[id_partie].nb_objets[i]):
                    if jeu[id_partie].objet[i][1+(o*5)] != "variable":
                        jeu[id_partie].objet[i][0+(o*5)] = jeu[id_partie].objet[i][0+(o*5)].lower()  # On enlève les majuscule du nom, sauf si c'est une variable
                        jeu[id_partie].objet[i][1+(o*5)] = jeu[id_partie].objet[i][1+(o*5)].lower()  # On enlève les majuscule au meuble aussi
                    jeu[id_partie].objet_reaction[jeu[id_partie].objet[i][0+(o*5)]] = []
                    if "§" in jeu[id_partie].objet[i][2+(o*5)]:  # On regarde si reaction dans examiner meuble
                        jeu[id_partie].objet[i][2+(o*5)] = jeu[id_partie].objet[i][2+(o*5)].split("§")
                        jeu[id_partie].meubleex_react.append(jeu[id_partie].objet[i][2+(o*5)][1])
                        jeu[id_partie].objet_reaction[jeu[id_partie].objet[i][0+(o*5)]].append(jeu[id_partie].objet[i][2+(o*5)][1])
                        jeu[id_partie].salle_reaction[str(int(jeu[id_partie].numero[i])-1)].append(jeu[id_partie].objet[i][2+(o*5)][1])
                        jeu[id_partie].objet[i][2+(o*5)] = jeu[id_partie].objet[i][2+(o*5)][0]
                    else:
                        jeu[id_partie].objet[i][2+(o*5)] = jeu[id_partie].objet[i][2+(o*5)].replace('+n+', '\n')  # description meuble
                        
                    if "§" in jeu[id_partie].objet[i][3+(o*5)]:  # On regarde si reaction dans prendre objet
                        jeu[id_partie].objet[i][3+(o*5)] = jeu[id_partie].objet[i][3+(o*5)].split("§")
                        jeu[id_partie].objetpr_react.append(jeu[id_partie].objet[i][3+(o*5)][1])
                        jeu[id_partie].objet_reaction[jeu[id_partie].objet[i][0+(o*5)]].append(jeu[id_partie].objet[i][3+(o*5)][1])
                        jeu[id_partie].salle_reaction[str(int(jeu[id_partie].numero[i])-1)].append(jeu[id_partie].objet[i][3+(o*5)][1])
                        jeu[id_partie].objet[i][3+(o*5)] = jeu[id_partie].objet[i][3+(o*5)][0]
                    else:
                        jeu[id_partie].objet[i][3+(o*5)] = jeu[id_partie].objet[i][3+(o*5)].replace('+n+', '\n')  # prendre objet
                        
                    if "§" in jeu[id_partie].objet[i][4+(o*5)]:  # On regarde si reaction dans examiner objet
                        jeu[id_partie].objet[i][4+(o*5)] = jeu[id_partie].objet[i][4+(o*5)].split("§")
                        jeu[id_partie].objetex_react.append(jeu[id_partie].objet[i][4+(o*5)][1])
                        jeu[id_partie].objet_reaction[jeu[id_partie].objet[i][0+(o*5)]].append(jeu[id_partie].objet[i][4+(o*5)][1])
                        jeu[id_partie].salle_reaction[str(int(jeu[id_partie].numero[i])-1)].append(jeu[id_partie].objet[i][4+(o*5)][1])
                        jeu[id_partie].objet[i][4+(o*5)] = jeu[id_partie].objet[i][4+(o*5)][0]
                    else:
                        jeu[id_partie].objet[i][4+(o*5)] = jeu[id_partie].objet[i][4+(o*5)].replace('+n+', '\n')  # description objet

                    if jeu[id_partie].objet[i][1+(o*5)] == "variable":
                        jeu[id_partie].variables[jeu[id_partie].objet[i][0+(o*5)]] = 0
                        jeu[id_partie].variables_description[jeu[id_partie].objet[i][0+(o*5)]] = lire_variable(interaction, jeu[id_partie].objet[i][4+(o*5)])
                    else:
                        jeu[id_partie].description[jeu[id_partie].objet[i][0+(o*5)]] = jeu[id_partie].objet[i][4+(o*5)]
                    
            j += 1
            direction = []
            
            while "*****" not in jeu[id_partie].scenario[i+j]:  # Pour chaque salle explorable à partir de l'emplacement.
                ligne = jeu[id_partie].scenario[i+j].replace("+n+", "\n")
                reaction_event = 0
                if "|" not in ligne:
                    direction.append(ligne)
                else:
                    ligne = ligne.split("|")
                    if ligne[0] == "997":
                            
                        if "§" in ligne[1]:
                            temp = ligne[1].split("§")[1]
                            ligne[1] = ligne[1].split("§")[0].split(" ")
                            ligne[1].append("§"+str(temp))
                            jeu[id_partie].salle_reaction[str(int(jeu[id_partie].numero[i])-1)].append(temp)
                            jeu[id_partie].event_react.append(ligne)
                        else : 
                            ligne[1] = ligne[1].split(" ")
                    
                      # else:  # +numéro de salle pour les actions locales
                                    # jeu[id_partie].action_reaction[emoji[0]+":"+str(i+1)] = objet.split("§")[1]
                                    # jeu[id_partie].action_reaction_inv[objet.split("§")[1]] = emoji[0] + ":" + str(i+1)
                    
                    elif ":" in ligne[0]:  # Action custom
                        if "§" in ligne[1]:
                            temp = ligne[1].split("§")[1]
                            ligne[1] = ligne[1].split("§")[0].split(" ")
                            ligne[1].append("§"+str(temp))
                            jeu[id_partie].action_reaction[ligne[0]+":"+str(i+1)] = temp
                            jeu[id_partie].action_reaction_inv[temp] = ligne[0] + ":" + str(i+1)
                        else : 
                            ligne[1] = ligne[1].split(" ")
                    elif ligne[0] not in ("998", "999"):
                        ligne[1] = ligne[1].split(" ")
                    direction.append(ligne)
                    
                j += 1

            jeu[id_partie].case.append(direction)
            i += 1
        case_actuelle = i + j

        for ligne in range(case_actuelle, len(jeu[id_partie].scenario)):  # Pour chaque ligne après la dernière salle
            ligne_actuelle = jeu[id_partie].scenario[ligne]
            # On regarde le premier élément d'une ligne pour déterminer son utilité
            if ":" in ligne_actuelle.split("|")[0]:  # Action custom
                ligne_actuelle = ligne_actuelle.split("|")
                if "§" in ligne_actuelle[1]:
                    temp = ligne_actuelle[1].split("§")[1]
                    ligne_actuelle[1] = ligne_actuelle[1].split("§")[0].split(" ")
                    ligne_actuelle[1].append("§"+str(temp))
                    jeu[id_partie].action_reaction[ligne_actuelle[0]+":"+"all"] = temp
                    jeu[id_partie].action_reaction_inv[temp] = ligne_actuelle[0] + ":" + "all"
                else : 
                    ligne_actuelle[1] = ligne_actuelle[1].split(" ")
                jeu[id_partie].action_custom.append(ligne_actuelle)
            
            elif "§" in ligne_actuelle.split("|")[0]:  # Alias des réactions
                alias_react = jeu[id_partie].scenario[ligne].split("|")
                for element in alias_react:
                    if '§' in element:
                        element = element.split("§")
                        jeu[id_partie].alias_reaction[element[0]] = element[1]
                        jeu[id_partie].alias_reaction_inv[element[1]] = element[0]
            
            elif "_o" in ligne_actuelle.split("|")[0]:  # Variables_online (variable_o)
                var_onl = jeu[id_partie].scenario[ligne].split("|")
                if var_onl[1].isdigit():
                    if var_onl[0] in jeu[id_partie].variables_online[jeu[id_partie].id_scenario]:
                        jeu[id_partie].variables[var_onl[0]] = int(jeu[id_partie].variables_online[jeu[id_partie].id_scenario][var_onl[0]])
                    else:
                        jeu[id_partie].variables_online[jeu[id_partie].id_scenario][var_onl[0]] = int(var_onl[1])
                        jeu[id_partie].variables[var_onl[0]] = int(var_onl[1])
                else:
                    if var_onl[0] in jeu[id_partie].variables_online[jeu[id_partie].id_scenario]:
                        jeu[id_partie].variables_texte[var_onl[0]] = str(jeu[id_partie].variables_online[jeu[id_partie].id_scenario][var_onl[0]])
                    else:
                        jeu[id_partie].variables_online[jeu[id_partie].id_scenario][var_onl[0]] = str(var_onl[1])
                        jeu[id_partie].variables_texte[var_onl[0]] = str(var_onl[1])
                jeu[id_partie].variables_description[var_onl[0]] = var_onl[2]
        
        if jeu[id_partie].id_scenario.startswith(url_certifiees):
            with open('variables_online.json', 'w') as var_o:
                json.dump(jeu[id_partie].variables_online, var_o, indent=4)

        jeu[id_partie].nom_salle = [x.lower() for x in jeu[id_partie].nom_salle]
        await envoyer_texte(interaction, jeu[id_partie].scenario[0])
        if jeu[id_partie].scenario[3] != "null":
            await envoyer_texte(interaction, jeu[id_partie].scenario[3], avec_reaction="ok")
        
        await verifier_objets(interaction)  # regarder si il y a des objets/conditions invisibles ou des variables
        
        await verifier_cases_speciales(interaction)  # vérifier si il y a des cases spéciales
        
        i = 0
        
    except:
        await interaction.send(f'```fix\n{lang[lang_id]["syntax_error_1"]} "{nom_scenario}" {lang[lang_id]["syntax_error_2"]} {int(i)+1}, {lang[lang_id]["syntax_error_3"]} {int(i+j+1)}.```')
        del jeu[id_partie]
        try:
            voice = get(bot.voice_clients, guild=interaction.guild)
            if voice.is_playing():
                voice.stop()
            await voice.disconnect()
        except:
            pass

@bot.slash_command()
async def jouer(interaction: nextcord.Interaction, nom_scenario: str = nextcord.SlashOption(required=False, default="...")):
    await jouer_cmd(interaction, nom_scenario)
    await avoid_failed(interaction)
    
@bot.slash_command()
async def play(interaction: nextcord.Interaction, nom_scenario: str = nextcord.SlashOption(required=False, default="...")):
    await jouer_cmd(interaction, nom_scenario)
    await avoid_failed(interaction)

async def avancer_cmd(interaction: nextcord.Interaction, choix="...", code="0"):
    """j!avancer X Y' avance dans la pièce X avec le code Y (si y'a un code)"""
    id_partie = str(interaction.guild_id)+str(interaction.channel_id)
    guilds = charger_guilds(interaction)
    lang_id = guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)]
    
    if "jdr-bot" not in interaction.channel.name:
        await interaction.send(f'```fix\n{lang[lang_id]["bad_channel"]}```')
        return
    
    if id_partie not in jeu:
        await interaction.send(f'```fix\n{lang[lang_id]["no_game_in_progress"]}```')
        return
    if choix == "...":
        await interaction.send(f'```fix\n{lang[lang_id]["move_where1"]}/{lang[lang_id]["move_where2"]}```')
        return
    if choix == "0":
        choix = str(jeu[id_partie].emplacement_precedent+1)
    choix = str(choix).lower()
    test = 0
    if choix in jeu[id_partie].options.keys():
        if choix != str(jeu[id_partie].emplacement+1) and choix != jeu[id_partie].nom_salle[jeu[id_partie].emplacement]:
            test = 1
    if choix in jeu[id_partie].nom_salle:
        choix = jeu[id_partie].nom_salle.index(choix)
        choix = str(int(choix)+1)
    
    try:
        i = 0
        test_condition = 0
        case_testee = 0
        if test == 0:
            for case in jeu[id_partie].case[jeu[id_partie].emplacement]:
                if isinstance(case, list):
                    case[0] = lire_variable(interaction,case[0])
                    if case[0] in jeu[id_partie].nom_salle:
                        case[0] = jeu[id_partie].nom_salle.index(case)
                        case[0] = str(int(case[0])+1)
                else:
                    case = lire_variable(interaction,case)
                    if case in jeu[id_partie].nom_salle:
                        case = jeu[id_partie].nom_salle.index(case)
                        case = str(int(case)+1)
                if isinstance(case, list) is False and choix != "997" and choix.startswith("action:") is False:   # Si la case contient juste un chiffre (= numero de salle) ou "retour"
                    if "->" in case:
                        if choix == case.split("->")[0]:
                            choix = case.split("->")[1]
                            test = 1
                            test_condition = 0
                            break
                    elif (case != "precedent" and case != "previous" and choix == case) or ((case == "precedent" or case == "previous") and choix == str(jeu[id_partie].emplacement_precedent+1)):  # On vérifie si c'est le numéro de salle choisis
                        test = 1
                        test_condition = 0
                        break
                elif isinstance(case, list) and choix != "997" and choix.startswith("action:") is False:  # autre si choix = numero
                    if "->" in case[0]:
                        if choix == case[0].split("->")[0]:
                            test = await condition_acces(interaction, case[1], code)
                            test_condition = 1
                            case_testee = i
                            if test == 1:
                                choix = case[0].split("->")[1]
                                break
                    else:
                        if (case[0] != "precedent" and case[0] != "previous" and choix == case[0]) or ((case[0] == "precedent" or case[0] == "previous") and choix == str(jeu[id_partie].emplacement_precedent+1)):
                            test = await condition_acces(interaction, case[1], code)
                            test_condition = 1
                            case_testee = i
                            if test == 1:
                                break
                i += 1
        if test == 2:
            if jeu[id_partie].case[jeu[id_partie].emplacement][case_testee][2] != "null":
                await envoyer_texte(interaction, jeu[id_partie].case[jeu[id_partie].emplacement][case_testee][2])
        if test == 1:
            if test_condition == 1:
                if jeu[id_partie].case[jeu[id_partie].emplacement][case_testee][3] != "null":
                    await envoyer_texte(interaction, jeu[id_partie].case[jeu[id_partie].emplacement][case_testee][3])
                if "$" in jeu[id_partie].case[jeu[id_partie].emplacement][case_testee][1]:
                    jeu[id_partie].case[jeu[id_partie].emplacement][case_testee] = jeu[id_partie].case[jeu[id_partie].emplacement][case_testee][0]
                        
            try:
                jeu[id_partie].variables["valeur"] = int(code)
                jeu[id_partie].variables["value"] = int(code)
                jeu[id_partie].emplacement_precedent = jeu[id_partie].emplacement
                jeu[id_partie].emplacement = int(choix)-1
                if jeu[id_partie].texte[jeu[id_partie].emplacement] != "null":
                    await envoyer_texte(interaction, jeu[id_partie].texte[jeu[id_partie].emplacement], avec_reaction="ok")
                await verifier_objets(interaction)  # regarder si il y a des objets/conditions invisibles ou des variables
                await verifier_cases_speciales(interaction, code)
            except ValueError:
                await interaction.send(f'```fix\n{lang[lang_id]["move_2nd_argument"]}```')

        elif test != 2:
            await interaction.send(f'```fix\n{lang[lang_id]["impossible_choice"]}```')
    except IndexError:
        await interaction.send(f'```fix\n{lang[lang_id]["wrong_nb_rooms"]}```')
    except:
        pass  # Arrive lorsque le scénario ou discord envoie une redirection après la fermeture du scénario (= keyerror)

@bot.slash_command()
async def avancer(interaction: nextcord.Interaction, choix: str = nextcord.SlashOption(required=True), code: str = nextcord.SlashOption(required=False, default="0")):
    await avancer_cmd(interaction, choix, code)
    await avoid_failed(interaction)

@bot.slash_command()
async def go(interaction: nextcord.Interaction, choix: str = nextcord.SlashOption(required=True), code: str = nextcord.SlashOption(required=False, default="0")):
    await avancer_cmd(interaction, choix, code)
    await avoid_failed(interaction)

async def reculer_cmd(interaction: nextcord.Interaction, code="0"):
    id_partie = str(interaction.guild_id)+str(interaction.channel_id)
    guilds = charger_guilds(interaction)
    lang_id = guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)]
    
    if "jdr-bot" not in interaction.channel.name:
        await interaction.send(f'```fix\n{lang[lang_id]["bad_channel"]}```')
        return
    
    if id_partie not in jeu:
        await interaction.send(f'```fix\n{lang[lang_id]["no_game_in_progress"]}```')
        return
    await avancer_cmd(interaction, str(jeu[id_partie].emplacement_precedent+1), code)

@bot.slash_command()
async def reculer(interaction: nextcord.Interaction, code: str = nextcord.SlashOption(required=False, default="0")):
    await reculer_cmd(interaction, code)
    await avoid_failed(interaction)
    
@bot.slash_command()
async def back(interaction: nextcord.Interaction, code: str = nextcord.SlashOption(required=False, default="0")):
    await reculer_cmd(interaction, code)
    await avoid_failed(interaction)


async def prendre_cmd(interaction: nextcord.Interaction, objet_cible="...", par_reponse=0):
    """j!prendre X' prend l'objet X"""
    id_partie = str(interaction.guild_id)+str(interaction.channel_id)
    guilds = charger_guilds(interaction)
    lang_id = guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)]
    
    if "jdr-bot" not in interaction.channel.name:
        await interaction.send(f'```fix\n{lang[lang_id]["bad_channel"]}```')
        return
    
    objet_cible = objet_cible.lower()
    i = 0
    try:
        for o in range(jeu[id_partie].nb_objets[jeu[id_partie].emplacement]):
            if objet_cible == jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)]:  # si cible = un des objets de la pièce, cible2 = "test1" (objet) et i = n° de l'objet
                i = o
                break
        if objet_cible == jeu[id_partie].objet[jeu[id_partie].emplacement][0+(i*5)] and objet_cible != "null":
            if jeu[id_partie].objet[jeu[id_partie].emplacement][1+(i*5)] == "invisible" or jeu[id_partie].objet[jeu[id_partie].emplacement][1+(i*5)] == "variable":
                await interaction.send(f'```fix\n{lang[lang_id]["no_object"]}```')
            elif jeu[id_partie].objet[jeu[id_partie].emplacement][0+(i*5)] != "|" and jeu[id_partie].objet[jeu[id_partie].emplacement][0+(i*5)] not in jeu[id_partie].inventaire_en_cours:
                jeu[id_partie].inventaire_en_cours.append(jeu[id_partie].objet[jeu[id_partie].emplacement][0+(i*5)])
                jeu[id_partie].objet[jeu[id_partie].emplacement][0+(i*5)] = "null"
                if jeu[id_partie].objet[jeu[id_partie].emplacement][3+(i*5)] != "null":
                    await envoyer_texte(interaction, jeu[id_partie].objet[jeu[id_partie].emplacement][3+(i*5)])
                if objet_cible in jeu[id_partie].objet_reaction.keys():
                    try:
                        for element in jeu[id_partie].objet_reaction[objet_cible]:
                            jeu[id_partie].salle_reaction[str(jeu[id_partie].emplacement)].remove(element)
                    except:
                        pass
                                
                await verifier_cases_speciales(interaction, code="0")  # prendre un objet reverifie et redéclenche les 997 comme lors de l'entrée dans une salle.

            else:
                await interaction.send(f'```fix\n{lang[lang_id]["object_picked_up"]} \"{objet_cible}\".```')
        elif objet_cible == "...":
            await interaction.send(f'```fix\n{lang[lang_id]["object_target1"]} /{lang[lang_id]["object_target2"]}```')
        else:
            if par_reponse == 0:
                await interaction.send(f'```fix\n{lang[lang_id]["object_unknown"]} \"{objet_cible}\"```')
            else:
                await interaction.send(f'```fix\n{lang[lang_id]["incorrect_answer1"]} \"{objet_cible}\" {lang[lang_id]["incorrect_answer2"]}```')
    except:
        await interaction.send(f'```fix\n{lang[lang_id]["game_in_progress_error"]}```')

@bot.slash_command()
async def prendre(interaction: nextcord.Interaction, objet_cible: str = nextcord.SlashOption(required=True, default="...")):
    await prendre_cmd(interaction, objet_cible)
    await avoid_failed(interaction)

@bot.slash_command()
async def take(interaction: nextcord.Interaction, objet_cible: str = nextcord.SlashOption(required=True, default="...")):
    await prendre_cmd(interaction, objet_cible)
    await avoid_failed(interaction)
    

async def examiner_cmd(interaction: nextcord.Interaction, cible="ici"):
    """j!examiner [element]' examine l'élément (endroit de la pièce, objet de la pièece ou de l'inventaire, etc.). Par défaut : examine la pièce où on se trouve."""
    id_partie = str(interaction.guild_id)+str(interaction.channel_id)
    guilds = charger_guilds(interaction)
    lang_id = guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)]
    
    if "jdr-bot" not in interaction.channel.name:
        await interaction.send(f'```fix\n{lang[lang_id]["bad_channel"]}```')
        return
    
    i = 0
    cible2 = ""
    try:
        if cible not in jeu[id_partie].variables:
            cible = cible.lower()
        for o in range(jeu[id_partie].nb_objets[jeu[id_partie].emplacement]):
            if cible == jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)]:  # si cible = un des objets de la pièce, cible2 = "objet" et i = n° de l'objet
                cible2 = "objet"
                i = o
                break
            elif cible == jeu[id_partie].objet[jeu[id_partie].emplacement][1+(o*5)] and jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)] != "null":  # si cible = un des meubles de la pièce, cible2 = "meuble" et i = n° de l'objet
                cible2 = "meuble"
                i = o
                break

        if cible == "ici":
            await envoyer_texte(interaction, jeu[id_partie].texte[jeu[id_partie].emplacement], avec_reaction="ok")
        elif cible == "invisible" or cible == "variable" or cible[0] == "-" or cible == "null":
            await interaction.send(f'```fix\n{lang[lang_id]["look_impossible"]}```')
        elif cible in jeu[id_partie].variables:
            if "(S)" not in cible:
                await interaction.send(f'```fix\n{cible} : {jeu[id_partie].variables[cible]}```')
            await envoyer_texte(interaction, jeu[id_partie].variables_description[cible])
        elif cible in jeu[id_partie].variables_texte:
            await envoyer_texte(interaction, jeu[id_partie].variables_texte[cible])
            await envoyer_texte(interaction, jeu[id_partie].variables_description[cible])
        elif cible in jeu[id_partie].inventaire_en_cours or cible in jeu[id_partie].inventaire_invisible or cible2 == "objet":
            await envoyer_texte(interaction, jeu[id_partie].description[cible])
        elif jeu[id_partie].objet[jeu[id_partie].emplacement][0+(i*5)] != "|":
            if cible2 == "meuble":
                if jeu[id_partie].objet[jeu[id_partie].emplacement][0+(i*5)] not in jeu[id_partie].inventaire_en_cours:
                    await envoyer_texte(interaction, jeu[id_partie].objet[jeu[id_partie].emplacement][2+(i*5)])
                else:
                    await interaction.send(f'```fix\n{lang[lang_id]["look_nothing"]}```')
            else:
                await interaction.send(f'```fix\n{lang[lang_id]["look_what"]}```')
        else:
            await interaction.send(f'```fix\n{lang[lang_id]["look_what"]}```')
    except:
        await interaction.send(f'```fix\n{lang[lang_id]["game_in_progress_error"]}```')

@bot.slash_command()
async def examiner(interaction: nextcord.Interaction, cible: str = nextcord.SlashOption(required=False, default="ici")):
    await examiner_cmd(interaction, cible)
    await avoid_failed(interaction)

@bot.slash_command()
async def inspect(interaction: nextcord.Interaction, cible: str = nextcord.SlashOption(required=False, default="ici")):
    await examiner_cmd(interaction, cible)
    await avoid_failed(interaction)
    

async def modifier_cmd(interaction: nextcord.Interaction, variable="...", valeur=0):
    """Affiche l'inventaire du joueur"""
    id_partie = str(interaction.guild_id)+str(interaction.channel_id)
    guilds = charger_guilds(interaction)
    lang_id = guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)]
    
    if "jdr-bot" not in interaction.channel.name:
        await interaction.send(f'```fix\n{lang[lang_id]["bad_channel"]}```')
        return
    
    try:
        if id_partie in jeu:
            if variable == "...":
                await interaction.send(f'```fix\n{lang[lang_id]["edit_error1"]}/{lang[lang_id]["edit_error2"]}```')
            elif variable in jeu[id_partie].variables:
                if "(M)" in variable:
                    jeu[id_partie].variables[variable] = int(valeur)
                    await interaction.send(f'```fix\n{lang[lang_id]["edit_done"]}, {variable} = {valeur}.```')
                    
                    await verifier_cases_speciales(interaction, code="0")  # modifier une variable reverifie et redéclenche les 997 comme lors de l'entrée dans une salle.
                                    
                else:
                    await interaction.send(f'```fix\n{lang[lang_id]["edit_impossible"]}```')
            else:
                await interaction.send(f'```fix\n{lang[lang_id]["edit_unknown"]}```')
        else:
            await interaction.send(f'```fix\n{lang[lang_id]["no_game_in_progress"]}```')
    except:
        await interaction.send(f'```fix\n{lang[lang_id]["edit_error1"]}/{lang[lang_id]["edit_error2"]}```')

@bot.slash_command()
async def modifier(interaction: nextcord.Interaction, variable: str = nextcord.SlashOption(required=True), valeur: int = nextcord.SlashOption(required=True)):
    await modifier_cmd(interaction, variable, valeur)
    await avoid_failed(interaction)

@bot.slash_command()
async def edit(interaction: nextcord.Interaction, variable: str = nextcord.SlashOption(required=True), valeur: int = nextcord.SlashOption(required=True)):
    await modifier_cmd(interaction, variable, valeur)
    await avoid_failed(interaction)


async def repondre_cmd(interaction: nextcord.Interaction, valeur="..."):
    id_partie = str(interaction.guild_id)+str(interaction.channel_id)
    guilds = charger_guilds(interaction)
    lang_id = guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)]
    
    if "jdr-bot" not in interaction.channel.name:
        await interaction.send(f'```fix\n{lang[lang_id]["bad_channel"]}```')
        return
    
    var = 0
    if id_partie not in jeu:
        await interaction.send(f'```fix\n{lang[lang_id]["no_game_in_progress"]}```')
        return
    variable_texte = ""
    for i in range(jeu[id_partie].nb_objets[jeu[id_partie].emplacement]):
        if jeu[id_partie].objet[jeu[id_partie].emplacement][i*5+1] == "variable_t":
            variable_texte = jeu[id_partie].objet[jeu[id_partie].emplacement][i*5]
            var = i
    if valeur == "...":
        await envoyer_texte(interaction, lang[lang_id]["reply_argument"])
    elif variable_texte != "":
        jeu[id_partie].variables_texte[variable_texte] = valeur
        if variable_texte.endswith("_o"):
            if jeu[id_partie].id_scenario.startswith(url_certifiees):
                jeu[id_partie].variables_online[jeu[id_partie].id_scenario][variable_texte] = jeu[id_partie].variables_texte[variable_texte]
                with open('variables_online.json', 'w') as var_o:
                    json.dump(jeu[id_partie].variables_online, var_o, indent=4)
        if jeu[id_partie].objet[jeu[id_partie].emplacement][var*5+3] != "null":
            await envoyer_texte(interaction, jeu[id_partie].objet[jeu[id_partie].emplacement][var*5+3])
        await verifier_cases_speciales(interaction, code="0")
    else:
        try:
            jeu[id_partie].variables["reponse"] = int(valeur)
            jeu[id_partie].variables["answer"] = int(valeur)
            await verifier_cases_speciales(interaction, code="0")
        except:
            await prendre_cmd(interaction, str(valeur), 1)

@bot.slash_command()
async def repondre(interaction: nextcord.Interaction, valeur: str = nextcord.SlashOption(required=True)):
    await repondre_cmd(interaction, valeur)
    await avoid_failed(interaction)

@bot.slash_command()
async def reply(interaction: nextcord.Interaction, valeur: str = nextcord.SlashOption(required=True)):
    await repondre_cmd(interaction, valeur)
    await avoid_failed(interaction)


async def scenario_en_cours_cmd(interaction: nextcord.Interaction):
    """Affiche le scenario en cours"""
    id_partie = str(interaction.guild_id)+str(interaction.channel_id)
    guilds = charger_guilds(interaction)
    lang_id = guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)]
    
    if "jdr-bot" not in interaction.channel.name:
        await interaction.send(f'```fix\n{lang[lang_id]["bad_channel"]}```')
        return
    
    try:
        await interaction.send(f'```fix\n{lang[lang_id]["script_in_progresse"]} \"{jeu[id_partie].scenario[0]}\"```')
    except:
        await interaction.send(f'```fix\n{lang[lang_id]["no_game_in_progress"]}```')

@bot.slash_command()
async def scenario_en_cours(interaction: nextcord.Interaction):
    await scenario_en_cours_cmd(interaction)
    await avoid_failed(interaction)

@bot.slash_command()
async def current_script(interaction: nextcord.Interaction):
    await scenario_en_cours_cmd(interaction)
    await avoid_failed(interaction)


async def inventaire_cmd(interaction: nextcord.Interaction):
    """Affiche l'inventaire du joueur"""
    id_partie = str(interaction.guild_id)+str(interaction.channel_id)
    guilds = charger_guilds(interaction)
    lang_id = guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)]
    
    if "jdr-bot" not in interaction.channel.name:
        await interaction.send(f'```fix\n{lang[lang_id]["bad_channel"]}```')
        return
        
    if id_partie in jeu:
        embed = nextcord.Embed(color=0x17B93C, title = lang[lang_id]["inventory1"], description = lang[lang_id]["inventory2"])
        for objet in jeu[id_partie].inventaire_en_cours:
            embed.add_field(name=objet, value=jeu[id_partie].description[objet], inline=False)
        await interaction.send(embed=embed)
        message = await interaction.original_message()
        try:
            view = choixView(interaction)
            await message.edit(view=view)
        except:
            pass  # Si la réaction n'existe pas dans le scénario (erreur de l'auteur), le bot ignore
    else:
        await interaction.send(f'```fix\n{lang[lang_id]["no_game_in_progress"]}```')

@bot.slash_command()
async def inventaire(interaction: nextcord.Interaction):
        await inventaire_cmd(interaction)
        await avoid_failed(interaction)
        
@bot.slash_command()
async def inventory(interaction: nextcord.Interaction):
        await inventaire_cmd(interaction)
        await avoid_failed(interaction)


async def jeter_cmd(interaction: nextcord.Interaction, objet_jete="???"):
    """jette un objet par terre"""
    id_partie = str(interaction.guild_id)+str(interaction.channel_id)
    guilds = charger_guilds(interaction)
    lang_id = guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)]
    
    if "jdr-bot" not in interaction.channel.name:
        await interaction.send(f'```fix\n{lang[lang_id]["bad_channel"]}```')
        return
    
    if id_partie in jeu:
        if objet_jete == "???":
            await interaction.send(f'```fix\n{lang[lang_id]["throw_choose1"]} /{lang[lang_id]["throw_choose2"]}```')
        elif objet_jete in jeu[id_partie].inventaire_en_cours:
            jeu[id_partie].inventaire_en_cours.remove(objet_jete)
            await interaction.send(f'```fix\n{lang[lang_id]["throw_success"]} \"{objet_jete}\"```')
        else:
            await interaction.send(f'```fix\n\"{objet_jete.capitalize()}\" {lang[lang_id]["throw_unknown"]}```')
    else:
        await interaction.send(f'```fix\n{lang[lang_id]["no_game_in_progress"]}```')

@bot.slash_command()
async def jeter(interaction: nextcord.Interaction, objet_jete: str = nextcord.SlashOption(required=True)):
    await jeter_cmd(interaction, objet_jete)
    await avoid_failed(interaction)
    
@bot.slash_command()
async def throw(interaction: nextcord.Interaction, objet_jete: str = nextcord.SlashOption(required=True)):
    await jeter_cmd(interaction, objet_jete)
    await avoid_failed(interaction)


async def action_cmd(interaction: nextcord.Interaction, choix="...", cible="..."):
    """action personnalisée"""
    id_partie = str(interaction.guild_id)+str(interaction.channel_id)
    guilds = charger_guilds(interaction)
    lang_id = guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)]
    
    if "jdr-bot" not in interaction.channel.name:
        await interaction.send(f'```fix\n{lang[lang_id]["bad_channel"]}```')
        return
    
    try:
        test = 0
        texte = ""
        action_trouvee = 0
        if id_partie not in jeu:
            await interaction.send(f'```fix\n{lang[lang_id]["no_game_in_progress"]}```')
            return 0
        if choix == "...":
            await interaction.send(f'```fix\n{lang[lang_id]["action_argument"]}```')
        else:  # On verifie d'abord les actions locales
            jeu[id_partie].variables_texte["action_cible"] = cible
            jeu[id_partie].variables_texte["action_target"] = cible
            for case_verifiee in jeu[id_partie].case[jeu[id_partie].emplacement]:
                if isinstance(case_verifiee, list) is True:
                    if ":" in case_verifiee[0]:
                        if choix == case_verifiee[0].split(":")[0] and (cible == case_verifiee[0].split(":")[1] or case_verifiee[0].split(":")[1] == "all"):
                            jeu[id_partie].variables_texte["action_cible_ok"] = cible
                            jeu[id_partie].variables_texte["action_target_ok"] = cible
                            test = await condition_acces(interaction, case_verifiee[1], "0")
                            action_trouvee = 1
                            texte = case_verifiee[4]
                            if test == 1:
                                await executer_event(interaction, "0", case_verifiee)
                                break
            if test != 1:  # Ensuite les actions globales
                for element in jeu[id_partie].action_custom:
                    if choix == element[0].split(":")[0] and (cible == element[0].split(":")[1] or element[0].split(":")[1] == "all"):
                        jeu[id_partie].variables_texte["action_cible_ok"] = cible
                        jeu[id_partie].variables_texte["action_target_ok"] = cible
                        test = await condition_acces(interaction, element[1], "0")
                        action_trouvee = 1
                        texte = element[4]
                        if test == 1:
                            await executer_event(interaction, "0", element)
                            break
            if action_trouvee == 1 and test != 1 and texte != "null":
                await envoyer_texte(interaction, texte)
        if action_trouvee == 0 and choix != "...":
            await interaction.send(f'```fix\n{lang[lang_id]["action_impossible"]}```')
    except:
        pass

@bot.slash_command()
async def action(interaction: nextcord.Interaction, action: str = nextcord.SlashOption(required=True), cible: str = nextcord.SlashOption(required=False, default="...")):
    await action_cmd(interaction, action, cible)
    await avoid_failed(interaction)

async def abandonner_cmd(interaction: nextcord.Interaction):
    """Met fin à la partie par un abandon"""
    id_partie = str(interaction.guild_id)+str(interaction.channel_id)
    guilds = charger_guilds(interaction)
    lang_id = guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)]
    
    if "jdr-bot" not in interaction.channel.name:
        await interaction.send(f'```fix\n{lang[lang_id]["bad_channel"]}```')
        return
    
    if id_partie not in jeu:
        await interaction.send(f'```fix\n{lang[lang_id]["no_game_in_progress"]}```')
        return
    await interaction.send(f'```fix\n{lang[lang_id]["giveup"]}```')
    del jeu[id_partie]
    try:
        voice = get(bot.voice_clients, guild=interaction.guild)
        if voice.is_playing():
            voice.stop()
        await voice.disconnect()
    except:
        pass

@bot.slash_command()
async def abandonner(interaction: nextcord.Interaction):
    await abandonner_cmd(interaction)
    await avoid_failed(interaction)

@bot.slash_command()
async def giveup(interaction: nextcord.Interaction):
    await abandonner_cmd(interaction)  
    await avoid_failed(interaction)


# @bot.slash_command()
# async def debug(interaction: nextcord.Interaction):
    # """Information de debug"""
    # id_partie = str(interaction.guild_id)+str(interaction.channel_id)
    # if id_partie in jeu:
        # await interaction.send(f'```fix\n{jeu[id_partie].salle_react}```')
    # else:
       # await interaction.send(f'```fix\nIl n\'y a pas de partie en cours !```')
    # await avoid_failed(interaction)


async def help_cmd(interaction: nextcord.Interaction, page=2):
    """information sur le bot et son auteur"""
    current_time = time.time()
    difference = int(round(current_time - start_time))
    text = str(datetime.timedelta(seconds=difference))
    id_partie = str(interaction.guild_id)+str(interaction.channel_id)
    guilds = charger_guilds(interaction)
    lang_id = guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)]
    charger_url(interaction)
    view = helpView()
    if bot.user.avatar is None:
        avatar_bot = ""
    else:
        avatar_bot = bot.user.avatar.url
    if page == 2:
        lien[id_partie].faq_on = None
        page = 0
    if page == 0:
        lien[id_partie].num_page = 0
        embed = nextcord.Embed(color=0x29d9e2, title = "**JDR-Bot**", description = lang[lang_id]["faq"])
        embed.set_author(name = bot.user.name+"#"+bot.user.discriminator, icon_url = avatar_bot)
        embed.set_thumbnail(url = avatar_bot)
        embed.add_field(name = lang[lang_id]["faq_author"], value = "<@"+str(My_ID)+">", inline = True)
        embed.add_field(name = lang[lang_id]["faq_guild"], value = str(len(bot.guilds)), inline = True)
        embed.add_field(name = "**Uptime**", value = text, inline = True)
        embed.add_field(name = lang[lang_id]["faq_how1"], value = "`" + "/" + lang[lang_id]["faq_how2"]+"`", inline = True)
        embed.add_field(name = lang[lang_id]["faq_script1"], value = "`" + "/" + lang[lang_id]["faq_script2"]+"`", inline = True)
        embed.add_field(name = lang[lang_id]["faq_syntax1"], value = lang[lang_id]["faq_syntax2"], inline = True)
        embed.add_field(name = lang[lang_id]["faq_commands1"], value = lang[lang_id]["faq_commands2"], inline = False)
        embed.add_field(name = lang[lang_id]["faq_link"], value = "[Github](https://github.com/Cyril-Fiesta/jdr-bot) | [Wiki](https://www.cyril-fiesta.fr/jdr-bot-wiki/) | [Invitation]( https://cyril-fiesta.fr/jdrbot/) | [Discord](https://discord.com/invite/Z63DtVV)", inline = False)
        embed.add_field(name = lang[lang_id]["faq_joinus1"], value = lang[lang_id]["faq_joinus2"], inline = False)
    else:
        lien[id_partie].num_page = 1
        embed = nextcord.Embed(color=0x29d9e2, title = "**JDR-Bot**", description = "")
        embed.set_thumbnail(url = avatar_bot)
        embed.add_field(name = lang[lang_id]["faq_commands1"], value = lang[lang_id]["faq_commands3"], inline = True)
    
    if lien[id_partie].faq_on is None:
        await interaction.send(embed = embed, view=view)
        lien[id_partie].faq_on = await interaction.original_message()
    else:
        await lien[id_partie].faq_on.edit(embed = embed, view=view)

@bot.slash_command()
async def help(interaction: nextcord.Interaction):
    await help_cmd(interaction)
    await avoid_failed(interaction)


async def stats_cmd(interaction: nextcord.Interaction, lien_scenario="..."):
    with open('variables_online.json', 'r') as var_o:
        statistique_online = json.load(var_o)
        
    guilds = charger_guilds(interaction)
    lang_id = guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)]
    
    if "jdr-bot" not in interaction.channel.name:
        await interaction.send(f'```fix\n{lang[lang_id]["bad_channel"]}```')
        return
    
    if bot.user.avatar is None:
        avatar_bot = ""
    else:
        avatar_bot = bot.user.avatar.url
    
    if guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)] == "en":
        first_url = "http://cyril-fiesta.fr/jdr-bot/scripts/"
    else:
        first_url = "http://cyril-fiesta.fr/jdr-bot/scenarios/"
    
    nb_parties = 0
    lien_scenario = lien_scenario.lower()
    if lien_scenario != "...":
        if lien_scenario.endswith("/") is True:
            lien_scenario -= "/"
        if lien_scenario.endswith(".txt") is False:
            lien_scenario += ".txt"
        if lien_scenario.startswith("http") is False:  # Sans url, on essaye sur celle par défaut
            lien_scenario = first_url + lien_scenario

    if lien_scenario == "...":
        for element in statistique_online:
            nb_parties += statistique_online[element]["nb_parties_o"]
        embed = nextcord.Embed(color=0xfe1b00, title = lang[lang_id]["stats1"], description = lang[lang_id]["stats2"])
        embed.add_field(name=lang[lang_id]["stats_global"], value=f'{nb_parties}', inline=False)
        embed.add_field(name = lang[lang_id]["stats_number1"], value=f'`/{lang[lang_id]["stats_number2"]} `/statistiques https://cyril-fiesta.fr/jdr-bot/scenarios/chateau.txt`', inline=False)
    elif lien_scenario in statistique_online:
        embed = nextcord.Embed(color=0xfe1b00, title = lang[lang_id]["stats1"], description = f'{lang[lang_id]["stats_script"]} {lien_scenario}')
        embed.add_field(name=f'{lang[lang_id]["stats_global"]}', value=f'{statistique_online[lien_scenario]["nb_parties_o"]}', inline=False)
    else:
        embed = nextcord.Embed(color=0xfe1b00, title = lang[lang_id]["stats1"], description = lang[lang_id]["stats_incorrect"])
    
    embed.set_author(name=bot.user.name+"#"+bot.user.discriminator, icon_url=avatar_bot)
    embed.set_thumbnail(url=avatar_bot)
    await interaction.send(embed=embed)

@bot.slash_command()
async def stats(interaction: nextcord.Interaction, lien_scenario: str = nextcord.SlashOption(required=False, default="...")):
    await stats_cmd(interaction, lien_scenario)
    await avoid_failed(interaction)

class choix_categorie(nextcord.ui.Select):
    def __init__(self):
        categories = []
        for key in categories_scenarios.keys():
            categories.append(nextcord.SelectOption(label=key, description=categories_scenarios[key]))
        super().__init__(placeholder="Choisissez la catégorie", min_values=1, max_values=1, options=categories)
        
    async def callback(self, interaction: nextcord.Interaction):
        await liste_scenarios_cmd(interaction, categories_scenarios[self.values[0]])
        await avoid_failed(interaction)
        

class choix_en_jeu(nextcord.ui.Select):
    def __init__(self,interaction):
        id_partie = str(interaction.guild_id)+str(interaction.channel_id)
        guilds = charger_guilds(interaction)
        lang_id = guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)]
        
        if id_partie not in jeu:
            return
        choix = []
        deja_utilise = []
        try:
            test_precedent = 0  # On vérifie la présence de la direction "précédente" dans les direction de la case en cours
            for element in jeu[id_partie].case[jeu[id_partie].emplacement]:
                if "precedent" in element or "previous" in element:
                    test_precedent = 1
                    break
        
            for element in jeu[id_partie].options:
                if element.startswith("v_") or element.startswith("t_") or (element != "precedent" and element != "previous" and element != str(jeu[id_partie].emplacement+1) and element != jeu[id_partie].nom_salle[jeu[id_partie].emplacement]) or ((element == "precedent" or element == "previous") and test_precedent == 1):
                    if jeu[id_partie].options[element] not in deja_utilise :
                        choix.append(nextcord.SelectOption(label=jeu[id_partie].options[element]))
                        deja_utilise.append(jeu[id_partie].options[element])
        
            for case_verifiee in jeu[id_partie].case[jeu[id_partie].emplacement]:
                try:
                    alias = ""
                    if isinstance(case_verifiee, list) is False:
                        case = str(lire_variable(interaction,case_verifiee))
                    else:
                        case = str(lire_variable(interaction,case_verifiee[0]))
                    
                    if "->" in case:
                        alias = case.split("->")[0]
                        case = int(case.split("->")[1]) - 1
                    elif case == "precedent" or case == "previous":
                        case = jeu[id_partie].emplacement_precedent
                    elif ":" in case:
                        continue
                    else:
                        case = int(case) - 1
                
                    if alias != "" and alias in jeu[id_partie].alias_reaction:
                        if jeu[id_partie].alias_reaction[alias] not in deja_utilise:
                            choix.append(nextcord.SelectOption(label=jeu[id_partie].alias_reaction[alias]))
                            deja_utilise.append(jeu[id_partie].alias_reaction[alias])
                    elif case not in (996, 997, 998) and jeu[id_partie].salle_react[case] != "..." and (case != jeu[id_partie].emplacement_precedent or (case == jeu[id_partie].emplacement_precedent and not (("precedent" in jeu[id_partie].options or "previous" in jeu[id_partie].options) and test_precedent == 1))):
                        if jeu[id_partie].salle_react[case] not in deja_utilise:
                            choix.append(nextcord.SelectOption(label=jeu[id_partie].salle_react[case]))
                            deja_utilise.append(jeu[id_partie].salle_react[case])
                except:
                    pass
                
            if len(jeu[id_partie].salle_reaction[str(jeu[id_partie].emplacement)]) > 0:
                emojis = jeu[id_partie].salle_reaction[str(jeu[id_partie].emplacement)]
                for emoji in emojis:
                    if emoji not in deja_utilise:
                        choix.append(nextcord.SelectOption(label=emoji))
                        deja_utilise.append(emoji)
                    
            for element in jeu[id_partie].action_reaction:
                if element.split(":")[2] == str(jeu[id_partie].emplacement+1) or element.split(":")[2] == "all":
                    if jeu[id_partie].action_reaction[element] not in deja_utilise:
                        choix.append(nextcord.SelectOption(label=jeu[id_partie].action_reaction[element]))
                        deja_utilise.append(jeu[id_partie].action_reaction[element])
        except:
            pass
        super().__init__(placeholder="Action :", min_values=1, max_values=1, options=choix)
        
    async def callback(self, interaction: nextcord.Interaction):
        id_partie = str(interaction.guild_id)+str(interaction.channel_id)
        guilds = charger_guilds(interaction)
        lang_id = guilds[str(interaction.guild_id)]["lang-"+str(interaction.channel_id)]
        
        try:  # Si l'objet est déjà pris on aura un ValueError si on examine le meuble.
            if self.values[0] in jeu[id_partie].options_inv:
                
                if jeu[id_partie].options_inv[self.values[0]] == "rafraichir" or jeu[id_partie].options_inv[self.values[0]] == "refresh":
                    await examiner_cmd(interaction)
                        
                elif jeu[id_partie].options_inv[self.values[0]] == "inventaire" or jeu[id_partie].options_inv[self.values[0]] == "inventory":
                    await inventaire_cmd(interaction)
                        
                elif jeu[id_partie].options_inv[self.values[0]] == "precedent" or jeu[id_partie].options_inv[self.values[0]] == "previous":
                    await avancer_cmd(interaction, "0", "0")
                        
                else:
                    if jeu[id_partie].options_inv[self.values[0]].startswith("v_") or jeu[id_partie].options_inv[self.values[0]].startswith("t_"):
                        await examiner_cmd(interaction, jeu[id_partie].options_inv[self.values[0]][2:-2])
                    else:
                        await avancer_cmd(interaction, jeu[id_partie].options_inv[self.values[0]], "0")

            elif self.values[0] in jeu[id_partie].salle_react:
                await avancer_cmd(interaction, str(jeu[id_partie].salle_react.index(self.values[0])+1), "0")
                    
            elif self.values[0] in jeu[id_partie].alias_reaction.values():
                await avancer_cmd(interaction, jeu[id_partie].alias_reaction_inv[self.values[0]], "0")
                    
            elif self.values[0] in jeu[id_partie].action_reaction_inv:
                arguments = jeu[id_partie].action_reaction_inv[self.values[0]].split(":")
                await action_cmd(interaction, arguments[0], arguments[1]) 
                
                

            else:
                meuble = "???"
                objet = ""
                for cle in jeu[id_partie].objet_reaction:
                    if self.values[0] in jeu[id_partie].objet_reaction[cle]:
                        objet = cle
                        if objet in jeu[id_partie].objet[jeu[id_partie].emplacement]:
                            meuble = jeu[id_partie].objet[jeu[id_partie].emplacement].index(objet) + 1
                        break
                if self.values[0] in jeu[id_partie].meubleex_react and self.values[0] in jeu[id_partie].salle_reaction[str(jeu[id_partie].emplacement)]:
                    if isinstance(meuble, int):
                        await examiner_cmd(interaction, jeu[id_partie].objet[jeu[id_partie].emplacement][meuble])
                    else:
                        await examiner_cmd(interaction, "objet_inconnu...")
                            
                elif self.values[0] in jeu[id_partie].objetex_react and self.values[0] in jeu[id_partie].salle_reaction[str(jeu[id_partie].emplacement)]:
                    await examiner_cmd(interaction, objet)

                elif self.values[0] in jeu[id_partie].objetpr_react and self.values[0] in jeu[id_partie].salle_reaction[str(jeu[id_partie].emplacement)]:
                    await prendre_cmd(interaction, objet)
                    
                elif self.values[0] in jeu[id_partie].salle_reaction[str(jeu[id_partie].emplacement)]:
                    i = 0
                    for element in jeu[id_partie].event_react:

                        if "§"+str(self.values[0]) in element[1]:
                            verification = []
                            for objet in element[1]:
                                verification.append(objet)
                            pos = verification.index("§"+str(self.values[0]))
                            verification[pos] = "§"
                            if await condition_acces(interaction, verification, code="0") == 1:
                                await executer_event(interaction, "0", element)
                            else:
                                if element[4] != "null":
                                    await envoyer_texte(interaction, element[4], avec_reaction="ok")
                            break
                        i += 1
        except:
            pass
        await avoid_failed(interaction)
        
        
class choixView(nextcord.ui.View):
    def __init__(self,interaction):
        super().__init__(timeout=None)
        self.add_item(choix_en_jeu(interaction))
        
class categorieView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(choix_categorie())
        
    @nextcord.ui.button(emoji = "⏪", style=nextcord.ButtonStyle.success)
    async def script_precedent(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        id_partie = str(interaction.guild_id)+str(interaction.channel_id)
        if lien[id_partie].num_page > 0:
            lien[id_partie].num_page -= 1
        else:
            lien[id_partie].num_page = 0
        await liste_scenarios_cmd(interaction, lien[id_partie].categorie_actuel) 
    
    @nextcord.ui.button(emoji = "⏩", style=nextcord.ButtonStyle.success)
    async def script_suivant(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        id_partie = str(interaction.guild_id)+str(interaction.channel_id)
        lien[id_partie].num_page += 1
        await liste_scenarios_cmd(interaction, lien[id_partie].categorie_actuel)
        

class helpView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @nextcord.ui.button(emoji = "📋", style=nextcord.ButtonStyle.success)
    async def help_page(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        id_partie = str(interaction.guild_id)+str(interaction.channel_id)
        if lien[id_partie].num_page == 0:
            lien[id_partie].num_page = 1
        else:
            lien[id_partie].num_page = 0
        await help_cmd(interaction, lien[id_partie].num_page)


# bot.loop.create_task(list_servers())
bot.run(TOKEN)
