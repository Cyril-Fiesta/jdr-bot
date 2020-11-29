# JDR-Bot est mise à disposition selon les termes de la Licence Creative Commons Attribution - Partage dans les Mêmes Conditions 4.0 International.
# https://creativecommons.org/licenses/by-sa/4.0/

import random
import asyncio
import aiohttp
import json
# import os #A mettre si on veut tester un scénario en local.
import typing
import discord
import urllib.request
import re
import traceback
import sys
from bs4 import BeautifulSoup
import requests
import datetime, time
from discord.ext.commands import Bot
from discord import Game
from discord.ext import commands
from discord.voice_client import VoiceClient
from discord.utils import get
from discord import FFmpegPCMAudio
from copy import deepcopy

with open('config.json', 'r') as f: #token et id stocké sur un fichier externe
    config = json.load(f)

TOKEN = config['SECRET_TOKEN'] # Get at discordapp.com/developers/applications/me
My_ID = config['ID_DEV'] # mon id discord

#BOT_PREFIX = ("j!", "J!")

def get_prefix(bot, message):
    with open('prefixes.json', 'r') as f: 
        prefixes = json.load(f)
    if message.guild is None:
        return ("j!","J!")
    else:
        return prefixes[str(message.guild.id)]

bot = commands.Bot(command_prefix=get_prefix, case_insensitive=True)
bot.remove_command('help')

base_url = "http://cyril-fiesta.fr/jdr-bot/scenarios/"
start_time = time.time()
categories_scenarios = {"📖" : "fiction","🔐" : "escape-game","👩‍🏫" : "tutoriel","🧩" : "exemple","🎮" : "divers"}
url_certifiees = ("http://cyril-fiesta.fr/jdr-bot/scenarios/","http://cyril-fiesta.fr/jdr-bot2/")

jeu = {}
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
        self.variables = {"resultat" : 0,"valeur" : 0}
        self.variables_description = {"resultat" : "Résultat de ... quelque chose !", "valeur" : "Valeur de ... quelque chose !", "reponse" : "Réponse à une question ...","action_cible" : "dernière cible d'une action","action_cible_ok" : "dernière cible existante d'une action"}
        self.variables_texte = {"action_cible" : "null","action_cible_ok" : "null"}
        self.action_custom = []
        self.nb_objets = []
        self.salle_react = []
        self.objetpr_react = []
        self.objetex_react = []
        self.meubleex_react = []
        self.event_react = []
        self.objet_reaction = {} #Lie chaque reaction a l'objet correspondant
        self.salle_reaction = {} #Lie chaque réaction à la salle correspondante
        self.alias_reaction = {} #Lie chaque réaction à l'alias correspondant
        self.alias_reaction_inv = {} #Dictionnaire alias/reaction inversé pour l'utilisation des réactions
        self.action_reaction = {} #Lie chaque reaction à l'action correspndante
        self.action_reaction_inv = {} #Lie chaque action à la reaction correspndante
        self.last_reaction = ""
        self.case_auto = 0
        self.variables_online = {}
        self.variables_texte_online = {}
        self.id_scenario = ""
        self.reaction_en_cours = 0
#jeu[id_partie].variable

lien = {}
class Url:
    def __init__(self):
        self.url_lien = []
#lien[id_partie].variable


@bot.event
async def on_ready():
    activite = "j!help | JDR-Bot 1.8, le JDR textuel sur discord ! " + str(len(bot.guilds)) + " serveurs."
    activity = discord.Game(name=activite)
    await bot.change_presence(activity=activity)
    servers_list = ""
    i = 0
    print("Logged in as " + bot.user.name)
    print("--- BOT ONLINE ---")
    for element in bot.guilds:
        with open('prefixes.json', 'r') as f: 
            prefixes = json.load(f)
        
        if str(element.id) not in prefixes:
            prefixes[str(element.id)] = ("j!","J!")
    
        with open('prefixes.json', 'w') as f: 
            json.dump(prefixes, f, indent=4)
        
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
    activite = "j!help | JDR-Bot 1.8, le JDR textuel sur discord ! " + str(len(bot.guilds)) + " serveurs."
    activity = discord.Game(name=activite)
    await bot.change_presence(activity=activity)
    with open('prefixes.json', 'r') as f: 
        prefixes = json.load(f)
    
    prefixes[str(guild.id)] = ("j!","J!")
    
    with open('prefixes.json', 'w') as f: 
        json.dump(prefixes, f, indent=4)

@bot.event
async def on_guild_remove(guild):
    activite = "j!help | JDR-Bot 1.8, le JDR textuel sur discord ! " + str(len(bot.guilds)) + " serveurs."
    activity = discord.Game(name=activite)
    await bot.change_presence(activity=activity)
    with open('prefixes.json', 'r') as f: 
        prefixes = json.load(f)
    
    prefixes.pop(str(guild.id))
    
    with open('prefixes.json', 'w') as f: 
        json.dump(prefixes, f, indent=4)

@bot.event
async def on_reaction_add(reaction, user):
    ctx = await bot.get_context(reaction.message)
    id_partie = str(reaction.message.guild.id)+str(reaction.message.channel.id)
    if str(user) == "JDR-Bot#5773":
        pass
    elif id_partie not in jeu and "jdr-bot" in reaction.message.channel.name and reaction.emoji in categories_scenarios:
        await liste_scenarios(ctx,categories_scenarios[reaction.emoji])
    elif id_partie in jeu:
        if jeu[id_partie].reaction_en_cours == 0:
            try : #Si l'objet est déjà pris on aura un ValueError si on examine le meuble.
                if reaction.emoji in jeu[id_partie].options_inv:
                    if jeu[id_partie].options_inv[reaction.emoji] == "rafraichir":
                        jeu[id_partie].reaction_en_cours = 1
                        await examiner(ctx)
                        jeu[id_partie].reaction_en_cours = 0
                    elif jeu[id_partie].options_inv[reaction.emoji] == "inventaire":
                        jeu[id_partie].reaction_en_cours = 1
                        await inventaire(ctx)
                        jeu[id_partie].reaction_en_cours = 0
                    elif jeu[id_partie].options_inv[reaction.emoji] == "precedent":
                        jeu[id_partie].reaction_en_cours = 1
                        await avancer(ctx,"0",0)
                        jeu[id_partie].reaction_en_cours = 0
                    else:
                        jeu[id_partie].reaction_en_cours = 1
                        if jeu[id_partie].options_inv[reaction.emoji].startswith("v_") or jeu[id_partie].options_inv[reaction.emoji].startswith("t_"):
                            await examiner(ctx, jeu[id_partie].options_inv[reaction.emoji][2:-2])
                        else:
                            await avancer(ctx,jeu[id_partie].options_inv[reaction.emoji],0)
                        jeu[id_partie].reaction_en_cours = 0
                        
                    
                elif reaction.emoji in jeu[id_partie].salle_react:
                    jeu[id_partie].reaction_en_cours = 1
                    await avancer(ctx,str(jeu[id_partie].salle_react.index(reaction.emoji)+1),0)
                    jeu[id_partie].reaction_en_cours = 0
            
                elif reaction.emoji in jeu[id_partie].alias_reaction.values():
                    jeu[id_partie].reaction_en_cours = 1
                    await avancer(ctx,jeu[id_partie].alias_reaction_inv[reaction.emoji],0)
                    jeu[id_partie].reaction_en_cours = 0
                
                elif reaction.emoji in jeu[id_partie].action_reaction_inv:
                    jeu[id_partie].reaction_en_cours = 1
                    arguments = jeu[id_partie].action_reaction_inv[reaction.emoji].split(":")
                    await action(ctx,arguments[0],arguments[1])
                    jeu[id_partie].reaction_en_cours = 0
                
                else:
                    for cle in jeu[id_partie].objet_reaction:
                        if reaction.emoji in jeu[id_partie].objet_reaction[cle]:
                            objet = cle
                            if objet in jeu[id_partie].objet[jeu[id_partie].emplacement]:
                                meuble = jeu[id_partie].objet[jeu[id_partie].emplacement].index(objet) + 1
                            else:
                                meuble = "???"
                            break
                    if reaction.emoji in jeu[id_partie].meubleex_react and reaction.emoji in jeu[id_partie].salle_reaction[str(jeu[id_partie].emplacement)]:
                        if isinstance(meuble,int):
                            jeu[id_partie].reaction_en_cours = 1
                            await examiner(ctx, jeu[id_partie].objet[jeu[id_partie].emplacement][meuble])
                            jeu[id_partie].reaction_en_cours = 0
                        else:
                            jeu[id_partie].reaction_en_cours = 1
                            await examiner(ctx,"objet_inconnu...")
                            jeu[id_partie].reaction_en_cours = 0
                    elif reaction.emoji in jeu[id_partie].objetex_react and reaction.emoji in jeu[id_partie].salle_reaction[str(jeu[id_partie].emplacement)]:
                        jeu[id_partie].reaction_en_cours = 1
                        await examiner(ctx, objet)
                        jeu[id_partie].reaction_en_cours = 0
                    
                    elif reaction.emoji in jeu[id_partie].objetpr_react and reaction.emoji in jeu[id_partie].salle_reaction[str(jeu[id_partie].emplacement)]:
                        jeu[id_partie].reaction_en_cours = 1
                        await prendre(ctx, objet)
                        jeu[id_partie].reaction_en_cours = 0
                            
                    elif reaction.emoji in jeu[id_partie].salle_reaction[str(jeu[id_partie].emplacement)]:
                        jeu[id_partie].reaction_en_cours = 1
                        i = 0
                        for element in jeu[id_partie].event_react:
                            if reaction.emoji in element[1]:
                                verification = []
                                for objet in element[1]:
                                    verification.append(objet)
                                pos = verification.index(reaction.emoji)
                                verification[pos] = "§"
                                if await condition_acces(ctx,verification,code="0") == 1 and element[0] > 0:
                                    await executer_event(ctx,0,element)
                                    jeu[id_partie].event_react[i][0] -= 1
                                else:
                                    if element[4] != "null":
                                        await envoyer_texte(ctx,element[4])
                                break
                            i += 1
                        jeu[id_partie].reaction_en_cours = 0
                            
            except:
                pass
        
@bot.command(aliases=['prefix', 'change_prefix'])
@commands.guild_only()
@commands.has_permissions(manage_channels=True)
async def setprefix(ctx, prefix = "..."):
    with open('prefixes.json', 'r') as f: 
        prefixes = json.load(f)
    
    if prefix == "...":
        await ctx.send(f'Le prefix actuel est : {prefixes[str(ctx.guild.id)]}')
    elif prefix == "base":
        prefixes[str(ctx.guild.id)] = ("j!","J!")
        await ctx.send(f'Le prefix est maintenant : {prefixes[str(ctx.guild.id)]}')
    else:
        if prefix.lower() == prefix.upper():
            prefixes[str(ctx.guild.id)] = (prefix)
        else:
            prefixes[str(ctx.guild.id)] = (prefix.lower(),prefix.upper())
        await ctx.send(f'Le prefix est maintenant : {prefixes[str(ctx.guild.id)]}')
    with open('prefixes.json', 'w') as f: 
        json.dump(prefixes, f, indent=4)

@bot.event
async def on_command_error(ctx, error):
        # This prevents any commands with local handlers being handled here in on_command_error.
        if hasattr(ctx.command, 'on_error'):
            return
        
        ignored = (commands.errors.UnexpectedQuoteError,commands.errors.ExpectedClosingQuoteError, commands.UserInputError, IndexError, KeyError, discord.errors.Forbidden)
        
        # Allows us to check for original exceptions raised and sent to CommandInvokeError.
        # If nothing is found. We keep the exception passed to on_command_error.
        error = getattr(error, 'original', error)
        
        # Anything in ignored will return and prevent anything happening.
        if isinstance(error, ignored):
            return

        elif isinstance(error, commands.DisabledCommand):
            return await ctx.send(f'```fix\n{ctx.command} has been disabled.```')

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.author.send(f'```fix\n{ctx.command} n\'est pas disponible en message privé.```')
            except:
                pass
                
        elif isinstance(error, commands.errors.CheckFailure):
            if str(ctx.command) == "setprefix":
                return await ctx.send(f'```fix\nLa commande {ctx.command} n\'est utilisable que si vous avez l\'autorisation de gérer les salons.```')
            else:
                return await ctx.send(f'```fix\nLa commande {ctx.command} n\'est utilisable que dans le channel "jdr-bot".```')
                
        elif isinstance(error, commands.BadArgument):
            return await ctx.send(f'```fix\nIl y a une erreur dans les arguments de la commande {ctx.command}```')

        elif isinstance(error, discord.errors.HTTPException):
            return await ctx.send(f'```fix\nLe texte que vous essayez d\'afficher fait plus de 2000 caractères ou comporte une réaction inexistante sur discord.```')
            
        elif isinstance(error, commands.CommandNotFound):
            id_partie = str(ctx.guild.id)+str(ctx.channel.id)
            if id_partie not in jeu:
                return await ctx.send(f'```fix\nCette commande n\'existe pas ou n\'est pas disponible en dehors d\'une partie```')
            else:
                argument = ctx.message.content[2:]
                if " " in argument:
                    argument = argument.split(" ")
                    await action(ctx,argument[0], argument[1])
                else:
                    await action(ctx,argument)
         
        else:
            print('Ignoring exception in command {}:'.format(ctx.message.content), file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
            
def in_channel(channel_name):
    def predicate(ctx):
        return channel_name in ctx.message.channel.name
    return commands.check(predicate)

@bot.command()
async def ping(ctx):
    await ctx.send('Pong! `{0}ms`'.format(str(round(bot.latency, 3)*1000)[:3]))

@bot.command(aliases=['warn', 'maintenance'])
async def warning(ctx,*message): #Cette commande me permet de prevenir des maintenances, updates et restart du bot.
    """Réservée au developpeur du bot. Informe des maintenances, rédemarrages et mises à jour."""
    message = " ".join(message).replace('\n','').replace('+n+', '\n')
    if ctx.author.id == My_ID:  #mon id discord
        embed = discord.Embed(color=0x29d9e2, timestamp=ctx.message.created_at)
        embed.set_author(name=bot.user.name+"#"+bot.user.discriminator, icon_url=bot.user.avatar_url)
        embed.set_thumbnail(url=bot.user.avatar_url)
        embed.add_field(name=f"Sent by {ctx.message.author}", value=message)
        for element in bot.guilds:
            for channel in element.text_channels:
                if "jdr-bot" in str(channel):
                    try:
                        await channel.send(embed=embed)
                        await asyncio.sleep(0.5)
                    except:
                        continue

def charger_url(ctx): #On charge les url de base et de la description.
    global base_url
    id_partie = str(ctx.guild.id)+str(ctx.channel.id)
    
    if id_partie not in lien:
        lien[id_partie] = Url()
   
    if base_url not in lien[id_partie].url_lien:
        lien[id_partie].url_lien.append(base_url)
        
    try:
        topic = ctx.message.channel.topic.replace('\n',' ').lower().split(" ")
        for element in topic:
            url = ""
            if element.startswith("http:"):
                url = element
                if url.endswith("/") is False:
                    url += "/"
                if url not in lien[id_partie].url_lien:
                    lien[id_partie].url_lien.append(url)
    except:
        pass

@bot.command(aliases=['url', 'lien', 'link'])
@commands.guild_only()
@in_channel('jdr-bot')
async def lien_jdr(ctx,action = "...", lien_scenarios = "..."): 
    """Affiche ou Modifie l'url où se trouve les scénarios."""
    global base_url
    id_partie = str(ctx.guild.id)+str(ctx.channel.id)
    charger_url(ctx)
    
    lien_scenarios = lien_scenarios.lower()
    if lien_scenarios.endswith("/") is False:
        lien_scenarios += "/"
    authorperms = ctx.author.permissions_in(ctx.channel)
    
    if action == "..." or action == "liste" or action == "list" or authorperms.manage_channels is False:
        liste_url = []
        liste_url.append("Liste d\'url de scénarios :\n")
        for element in lien[id_partie].url_lien:
            liste_url.append(str(element)+"\n")
        liste = ''.join(liste_url)
        await ctx.send(f'```fix\n{liste}```')
    elif action == "default" or action == "base" or action == "reset":
        lien[id_partie].url_lien = [base_url]
        await ctx.send(f'```fix\nL\'url des scénarios est désormais : {lien[id_partie].url_lien[0]}```')
    elif action == "add" or action == "ajouter":
        if lien_scenarios.startswith("http"):
            if lien_scenarios not in lien[id_partie].url_lien:
                lien[id_partie].url_lien.append(lien_scenarios)
                await ctx.send(f'```fix\nL\'url est ajoutée à JDR-Bot.```')
            else:
                await ctx.send(f'```fix\nL\'url est déjà prise en compte par JDR-Bot.```')
        else:
            await ctx.send(f'```fix\nMerci d\'indiquer une url correcte.```')
    elif action == "retirer" or action == "remove":
        if lien_scenarios in lien[id_partie].url_lien:
            lien[id_partie].url_lien.remove(lien_scenarios)
            await ctx.send(f'```fix\nL\'url est retirée de JDR-Bot.```')
        else:
            await ctx.send(f'```fix\nCette url n\'est pas présente dans JDR-Bot.```')
    else :
        await ctx.send(f'```fix\n Merci de spécifier une action correcte ("ajouter", "base", "liste" ou "retirer")```')

@bot.command(aliases=['scenario', 'scenarios','script','scripts','list_scripts'])
@commands.guild_only()
@in_channel('jdr-bot')
async def liste_scenarios(ctx,categorie="base"):
    id_partie = str(ctx.guild.id)+str(ctx.channel.id)
    with open('prefixes.json', 'r') as f: 
        prefixes = json.load(f)
        
    charger_url(ctx)
    for url in lien[id_partie].url_lien:
        liste_existante = 0
        try:
            page = requests.get(url).text
            soup = BeautifulSoup(page,'html.parser')
            liste = ["Liste de scénarios de : ",url,"\n"]
            for node in soup.find_all('a'):
                if node.get('href').endswith('.txt'):
                    liste.append(node.get('href')+"\n")
            for element in liste:
                if "liste_scenarios" in element:
                    liste_existante = 1
            if liste_existante == 1:
                try:
                    liste_embed = urllib.request.urlopen(url+"liste_scenarios.txt").read().decode('utf-8') # utf-8 pour remote files, ANSI pour locales files
                    liste_embed = liste_embed.split("\n")
                    if categorie.lower() in categories_scenarios.values():
                        embed=discord.Embed(color=0x256CB0 ,title= "Liste " + categorie.capitalize() + " de : "+url, description="")
                        for scenarios in liste_embed:
                            scenarios = scenarios.split("|")
                            if scenarios[1].lower() == categorie.lower():
                                texte = scenarios[0] + " (" + scenarios[1] + ")"
                                if scenarios[2].lower() == "yes":
                                    texte += " " + str("🏞️")
                                if scenarios[3].lower() == "yes":
                                    texte += " " + str("🔊")
                                if scenarios[4].lower() == "yes":
                                    texte += " " + str("🙂")
                                embed.add_field(name=texte, value=scenarios[5], inline=False)
                        embed.add_field(name="Légende :", value="🏞️ : Avec images. 🔊 : Avec sons. 🙂 : Avec réactions.", inline=False)
                        await ctx.send(embed=embed)
                    else:
                        embed=discord.Embed(color=0x256CB0 ,title= "Catégories de scénarios :")
                        embed.add_field(name="Fiction 📖", value="Fiction interactive / Aventure dont Vous êtes le Héros.", inline=False)
                        embed.add_field(name="Escape-game 🔐", value="Escape-game, scénarios à énigmes, etc.", inline=False)
                        embed.add_field(name="Tutoriel 👩‍🏫", value="Guide/tutoriel de divers sujet", inline=False)
                        embed.add_field(name="Exemple 🧩", value="Scénarios d'exemple pour l'écriture de scénarios ou tester une fonctionnalité du bot.", inline=False)
                        embed.add_field(name="Divers 🎮", value="Jeux et scripts divers", inline=False)
                        embed.add_field(name="Utilisation", value="Cliquez sur la reaction correspondante à la catégorie que vous voulez affichez (inutilisable pendant une partie) ou utiliser la commande `" + prefixes[str(ctx.guild.id)][0] + "liste_scenarios nom_de_la_catégorie`.", inline=False)
                        message = await ctx.send(embed=embed)
                        for key in categories_scenarios.keys():
                            await message.add_reaction(key)
                except:
                    liste.remove("liste_scenarios.txt\n")
                    liste = ''.join(liste)
                    await ctx.send(f'```fix\n{liste}```')
            elif categorie.lower() not in categories_scenarios.values():
                liste = ''.join(liste)
                await ctx.send(f'```fix\n{liste}```')
        except:
            pass

def lire_variable(ctx, texte): #remplace v_variable_v par la valeur de variable
    id_partie = str(ctx.guild.id)+str(ctx.channel.id)
    with open('variables_online.json', 'r') as var_o: 
        jeu[id_partie].variables_online = json.load(var_o)
    for element in jeu[id_partie].variables_online[jeu[id_partie].id_scenario]:
        if element in jeu[id_partie].variables:
            jeu[id_partie].variables[element] = jeu[id_partie].variables_online[jeu[id_partie].id_scenario][element]
        else:
            jeu[id_partie].variables_texte[element] = jeu[id_partie].variables_online[jeu[id_partie].id_scenario][element]
        
    texte = str(texte)
    for element in jeu[id_partie].variables.keys():
        texte = texte.replace('v_'+element+'_v',str(jeu[id_partie].variables[element]))
    for element_t in jeu[id_partie].variables_texte.keys():
        texte = texte.replace('t_'+element_t+'_t',str(jeu[id_partie].variables_texte[element_t]))
    return texte
    
async def envoyer_texte(ctx, texte, avec_reaction = "..."): #Convertit les liens images et sons dans le texte, ainsi que le formattage.
    """Envoyer le texte sur discord après avoir séparé les images et les sons"""
    id_partie = str(ctx.guild.id)+str(ctx.channel.id)
    with open('prefixes.json', 'r') as f: 
        prefixes = json.load(f)
        
    texte = lire_variable(ctx, texte)
    texte = texte.replace("[[PREFIX]]",prefixes[str(ctx.guild.id)][0])
    texte = texte.replace("[[INVENTAIRE]]",", ".join(jeu[id_partie].inventaire_en_cours))
    for numero in range(len(jeu[id_partie].texte)):
        texte = texte.replace("[[SALLE:"+str(numero+1)+"]]",jeu[id_partie].texte[numero])
    texte = texte.replace("[[","|-*[[")
    texte = texte.replace("]]","|-*")
    texte = texte.replace("<<","|-*<<")
    texte = texte.replace(">>","|-*")
    texte = texte.replace("{{","|-*{{")
    texte = texte.replace("}}","|-*")
    texte = texte.split('|-*')
    for element in texte:
        if element.startswith("[[") is True: #afficher l'élément sans markdown
            element = element.replace("[[","")
            if element != "":
                message = await ctx.send(f'{element}')
        elif element.startswith("<<") is True :  
            element = element.replace("<<","")
            if element.lower().startswith("http"):
                voice = get(bot.voice_clients, guild=ctx.guild)
                try:
                    source = FFmpegPCMAudio(element, options='-loglevel quiet') #On ignore les erreurs de conversation. Dans le pire des cas, ce son ne sera pas joué (mauvaise url, mauvais format, etc.)
                    if voice.is_playing():  #Si is_playing() is True => arrêt du son, puis diffusion du nouveau.
                        voice.stop()
                    voice.play(source)
                except:
                    pass
            else: #Si c'est pas un son, c'est un message TTS
                msg = await ctx.send(f'{element}', tts=True)
                await msg.delete()
        elif element.startswith("{{") is True:
            element = element.replace("{{","")
            try:
                await asyncio.sleep(int(element))
            except:
                pass
        elif element != "":
            element = "```" + str(jeu[id_partie].markdown) + element + "```"
            message = await ctx.send(f'{element}')
            
    test_precedent = 0 #On vérifie la présence de la direction "précédente" dans les direction de la case en cours
    for element in jeu[id_partie].case[jeu[id_partie].emplacement]:
        if "precedent" in element:
            test_precedent = 1
            break
            
    if avec_reaction == "ok":
        try: #au cas où une réaction n'existe pas (erreur d'un auteur), le bot peut ignoré
            for element in jeu[id_partie].options:
                if element.startswith("v_") or element.startswith("t_") or (element != "precedent" and element != str(jeu[id_partie].emplacement+1) and element != jeu[id_partie].nom_salle[jeu[id_partie].emplacement]) or (element == "precedent" and test_precedent == 1):
                    await message.add_reaction(jeu[id_partie].options[element])
            
            for element in jeu[id_partie].action_reaction:
                if element.split(":")[2] == str(jeu[id_partie].emplacement+1) or element.split(":")[2] == "all":
                    await message.add_reaction(jeu[id_partie].action_reaction[element])
            
            jeu[id_partie].last_reaction = element
            for case_verifiee in jeu[id_partie].case[jeu[id_partie].emplacement]:
                alias = ""
                if isinstance(case_verifiee,list) is False:
                    case = str(case_verifiee)
                else:
                    case = str(case_verifiee[0])

                if "->" in case:
                        alias = case.split("->")[0]
                        case = int(case.split("->")[1]) - 1
                elif case == "precedent":
                    case = jeu[id_partie].emplacement_precedent
                elif ":" in case:
                    continue
                else:
                    case = int(case) - 1
                        
                if alias in jeu[id_partie].alias_reaction:
                    await message.add_reaction(jeu[id_partie].alias_reaction[alias])
                elif case not in (996,997,998) and jeu[id_partie].salle_react[case] != "..." and (case != jeu[id_partie].emplacement_precedent or (case == jeu[id_partie].emplacement_precedent and not ("precedent"  in jeu[id_partie].options and test_precedent == 1))):
                    await message.add_reaction(jeu[id_partie].salle_react[case])
                    
            if len(jeu[id_partie].salle_reaction[str(jeu[id_partie].emplacement)]) > 0:
                emojis = jeu[id_partie].salle_reaction[str(jeu[id_partie].emplacement)]
                for emoji in emojis:
                    await message.add_reaction(emoji)
        except:
            pass

async def verifier_objets(ctx): #Verifie les objets, variables et conditions présents dans une salle
    id_partie = str(ctx.guild.id)+str(ctx.channel.id)
    valeur = ""
    changement = 0
    if jeu[id_partie].objet[jeu[id_partie].emplacement][0] != "|" :
        for o in range(jeu[id_partie].nb_objets[jeu[id_partie].emplacement]):
            if jeu[id_partie].objet[jeu[id_partie].emplacement][1+(o*5)] == "invisible":
                jeu[id_partie].description[jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)]] = jeu[id_partie].objet[jeu[id_partie].emplacement][4+(o*5)]
                if jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)][0] != "-" and jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)] not in jeu[id_partie].inventaire_invisible:
                    jeu[id_partie].inventaire_invisible.append(jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)])
                    changement = 1
                elif jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)][0] == "-":
                    if jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)][1:] in jeu[id_partie].inventaire_invisible:
                        jeu[id_partie].inventaire_invisible.remove(jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)][1:])
                        changement = 1
                    elif jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)][1:] in jeu[id_partie].inventaire_en_cours:
                        jeu[id_partie].inventaire_en_cours.remove(jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)][1:])
                        changement = 1
            elif jeu[id_partie].objet[jeu[id_partie].emplacement][1+(o*5)] == "variable":
                jeu[id_partie].variables_description[jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)]] = lire_variable(ctx, jeu[id_partie].objet[jeu[id_partie].emplacement][4+(o*5)])
                try:
                    if "%" in jeu[id_partie].objet[jeu[id_partie].emplacement][2+(o*5)]:
                        valeur = lire_variable(ctx, jeu[id_partie].objet[jeu[id_partie].emplacement][2+(o*5)][2:])
                        valeur = valeur.split(":")
                        valeur = jeu[id_partie].objet[jeu[id_partie].emplacement][2+(o*5)][1] + str(random.randint(int(valeur[0]),int(valeur[1])))
                        jeu[id_partie].variables["resultat"] = valeur[1:]
                    else:
                        valeur = lire_variable(ctx, jeu[id_partie].objet[jeu[id_partie].emplacement][2+(o*5)])
                    if "+" not in valeur and "-" not in valeur:
                        jeu[id_partie].variables[jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)]] = int(valeur[1:])
                    else:
                        jeu[id_partie].variables[jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)]] = jeu[id_partie].variables[jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)]] + int(valeur)
                    changement = 1
                    
                    if jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)].endswith("_o"):
                        if jeu[id_partie].id_scenario.startswith(url_certifiees): #si c'est une variable_o 
                            jeu[id_partie].variables_online[jeu[id_partie].id_scenario][jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)]] = jeu[id_partie].variables[jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)]]
                            with open('variables_online.json', 'w') as var_o: 
                                json.dump(jeu[id_partie].variables_online, var_o, indent=4)
                        
                except:
                    await ctx.send(f'```fix\nErreur [001] dans la variable {jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)]} et sa valeur ajoutée {lire_variable(ctx, jeu[id_partie].objet[jeu[id_partie].emplacement][2+(o*5)])}```')
            elif jeu[id_partie].objet[jeu[id_partie].emplacement][1+(o*5)] == "variable_t":
                jeu[id_partie].variables_texte[jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)]] = lire_variable(ctx, jeu[id_partie].objet[jeu[id_partie].emplacement][2+(o*5)])
                jeu[id_partie].variables_description[jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)]] = lire_variable(ctx, jeu[id_partie].objet[jeu[id_partie].emplacement][4+(o*5)])
                
                if jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)].endswith("_o"):
                    if jeu[id_partie].id_scenario.startswith(url_certifiees): #si c'est une variable_o 
                        jeu[id_partie].variables_online[jeu[id_partie].id_scenario][jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)]] = jeu[id_partie].variables_texte[jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)]]
                        with open('variables_online.json', 'w') as var_o: 
                            json.dump(jeu[id_partie].variables_online, var_o, indent=4)
                                
            if jeu[id_partie].objet[jeu[id_partie].emplacement][1+(o*5)] == "invisible" or jeu[id_partie].objet[jeu[id_partie].emplacement][1+(o*5)] == "variable":
                if jeu[id_partie].objet[jeu[id_partie].emplacement][3+(o*5)] != "null" and changement == 1:
                    await envoyer_texte(ctx,jeu[id_partie].objet[jeu[id_partie].emplacement][3+(o*5)])

async def condition_acces(ctx,case_actuelle,code="0"): #Vérifie si les conditions d'accès à une salle sont respectées
    id_partie = str(ctx.guild.id)+str(ctx.channel.id)
    test = 2
    test_code = 0
    for objet_test in case_actuelle:  #on vérifie pour chaque objet requis et code
        try:  #On test si l'objet est un code, sinon ValueError, et si oui on test le code
            test_code = 1
            if int(objet_test) != int(code):
                test = 2
                break
            else:
                test = 1
        except ValueError: #c'est donc un objet (texte) ou une variable, on regarde s'il est dans l'inventaire
            if objet_test == "null":
                test = 1
                break
            elif "§" in objet_test: #si c'est une reaction, on ignore cette condition
                test = 1
            elif objet_test[0] == "$":
                test = 1
            elif objet_test[0] == '-':
                if objet_test[1:] in jeu[id_partie].inventaire_en_cours or objet_test[1:] in jeu[id_partie].inventaire_invisible:
                    test = 2
                    break
                else:
                    test = 1
            elif "." in objet_test:   ### A partir de là, vérifier si c'est une variable.[operateur].valeur (donc si y'a un ".")
                try: #Au cas où la variable indiqué n'existe pas, dù à une erreur dans le scénario 
                    objet_test = objet_test.split(".") #objet_test[0] = valeur/variable, [1] = opérateur, [2] = valeur/variable
                    if (objet_test[0].startswith("v_") or objet_test[2].startswith("v_")) and not (objet_test[0].startswith("t_") or objet_test[2].startswith("t_")):
                        if objet_test[1] == ">":
                            if int(lire_variable(ctx, objet_test[0])) > int(lire_variable(ctx, objet_test[2])):
                                test = 1
                            else:
                                test = 2
                                break
                        elif objet_test[1] == "<":
                            if int(lire_variable(ctx, objet_test[0])) < int(lire_variable(ctx, objet_test[2])):
                                test = 1
                            else:
                                test = 2
                                break
                        elif objet_test[1] == "=":
                            if int(lire_variable(ctx, objet_test[0])) == int(lire_variable(ctx, objet_test[2])):
                                test = 1
                            else:
                                test = 2
                                break
                        elif objet_test[1] == "<=":
                            if int(lire_variable(ctx, objet_test[0])) <= int(lire_variable(ctx, objet_test[2])):
                                test = 1
                            else:
                                test = 2
                                break
                        elif objet_test[1] == ">=":
                            if int(lire_variable(ctx, objet_test[0])) >= int(lire_variable(ctx, objet_test[2])):
                                test = 1
                            else:
                                test = 2
                                break
                        elif objet_test[1] == "!=":
                            if int(lire_variable(ctx, objet_test[0])) != int(lire_variable(ctx, objet_test[2])):
                                test = 1
                            else:
                                test = 2
                                break
                        elif objet_test[1] == "in":
                            limite = objet_test[2].split("-")
                            if int(lire_variable(ctx, objet_test[0])) in range(int(lire_variable(ctx, limite[0])),int(lire_variable(ctx, limite[1]))+1):
                                test = 1
                            else:
                                test = 2
                                break
                        elif objet_test[1] == "out":
                            limite = objet_test[2].split("-")
                            if int(lire_variable(ctx, objet_test[0])) not in range(int(lire_variable(ctx, limite[0])),int(lire_variable(ctx, limite[1]))+1):
                                test = 1
                            else:
                                test = 2
                                break
                        else:
                            test = 2
                            await ctx.send(f'```fix\n{".".join(objet_test)} est incorrect```')
                            break
                    elif objet_test[0].startswith("t_") or objet_test[2].startswith("t_"):
                        if objet_test[1] == "=":
                            if str(lire_variable(ctx, objet_test[0])) == str(lire_variable(ctx, objet_test[2])):
                                test = 1
                            else:
                                test = 2
                                break
                        elif objet_test[1] == "!=":
                            if str(lire_variable(ctx, objet_test[0])) != str(lire_variable(ctx, objet_test[2])):
                                test = 1
                            else:
                                test = 2
                                break
                        elif objet_test[1] == "in":
                            if str(lire_variable(ctx, objet_test[0])) in str(lire_variable(ctx, objet_test[2])):
                                test = 1
                            else:
                                test = 2
                                break
                        elif objet_test[1] == "out":
                            if str(lire_variable(ctx, objet_test[0])) not in str(lire_variable(ctx, objet_test[2])):
                                test = 1
                            else:
                                test = 2
                                break
                        else:
                            test = 2
                            await ctx.send(f'```fix\n{".".join(objet_test)} est incorrect```')
                            break
                except:
                    await ctx.send(f'```fix\nLe scénario comporte une syntaxe incorrecte : probablement une variable qui n\'existe pas.```')
                    test = 2
                    break
            else:
                if objet_test not in jeu[id_partie].inventaire_en_cours and objet_test not in jeu[id_partie].inventaire_invisible:
                    test = 2
                    break
                else:
                    test = 1
    return test
    
async def executer_event(ctx,code="0",case_verifiee=[]):
    id_partie = str(ctx.guild.id)+str(ctx.channel.id)
    nb_event = case_verifiee[2].split("@@")
    afficher_texte = 0
    for element in nb_event:
        try:
            if element.startswith("v_") and element.endswith("_v"):
                element = str(jeu[id_partie].variables[element[2:-2]])
                if int(element) < 1 or int(element) > len(jeu[id_partie].numero) or int(element) == (jeu[id_partie].emplacement+1):
                    element = "null"
            if element.isdigit():
                temporaire = case_verifiee[3] #on garde de coté le texte de l'event si y'a pas d'erreur
                jeu[id_partie].emplacement_precedent = jeu[id_partie].emplacement
                jeu[id_partie].emplacement = int(element)-1
                if temporaire != "null": #pas d'erreur (except) ni de texte null, on envoit
                    await envoyer_texte(ctx,temporaire)
                if jeu[id_partie].texte[jeu[id_partie].emplacement] != "null":
                    await envoyer_texte(ctx,jeu[id_partie].texte[jeu[id_partie].emplacement],avec_reaction="ok")
                jeu[id_partie].case_auto += 1
                await verifier_objets(ctx)
                if jeu[id_partie].case_auto > 25:
                    return "break"
                await verifier_cases_speciales(ctx,code)
                return "break"
            elif element == "null":
                if case_verifiee[3] != "null":
                    afficher_texte = 1
            elif "&&" in element:
                try:
                    objet_temp = element.split("&&")

                    if objet_temp[1] == "inventaire":
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
                            pass  #s'il n'y a pas de changement, on ignore le 997, contrairement à !prendre qui affiche un texte
                    
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
                            pass  #s'il n'y a pas de changement, on ignore le 997, contrairement à !prendre qui affiche un texte
                    
                    elif objet_temp[1] == "variable": 
                        jeu[id_partie].variables[objet_temp[0]] = int(lire_variable(ctx,objet_temp[2]))
                        jeu[id_partie].variables_description[objet_temp[0]] = str(objet_temp[3])
                        if case_verifiee[3] != "null":
                            afficher_texte = 1
                        if objet_temp[0].endswith("_o"):
                            if jeu[id_partie].id_scenario.startswith(url_certifiees):
                                jeu[id_partie].variables_online[jeu[id_partie].id_scenario][objet_temp[0]] = jeu[id_partie].variables[objet_temp[0]]
                                with open('variables_online.json', 'w') as var_o: 
                                    json.dump(jeu[id_partie].variables_online, var_o, indent=4)
                    
                    elif objet_temp[1] == "variable_t":
                        jeu[id_partie].variables_texte[objet_temp[0]] = str(objet_temp[2])
                        jeu[id_partie].variables_description[objet_temp[0]] = str(objet_temp[3])
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
                try:
                    valeur = ""
                    variable_modifiee = element.split(".")

                    if variable_modifiee[0].endswith("_o"):
                        with open('variables_online.json', 'r') as var_o: 
                            jeu[id_partie].variables_online = json.load(var_o)
                        jeu[id_partie].variables[variable_modifiee[0]] = jeu[id_partie].variables_online[jeu[id_partie].id_scenario][variable_modifiee[0]]
                        
                    if not isinstance(variable_modifiee[2],int):
                        variable_modifiee[2] = lire_variable(ctx, variable_modifiee[2])
                    if variable_modifiee[0] not in jeu[id_partie].variables:   
                        jeu[id_partie].variables[variable_modifiee[0]] = 0
                        jeu[id_partie].variables_description[variable_modifiee[0]] = "..."
                    if "%" in variable_modifiee[2]:
                        valeur = variable_modifiee[2][1:].split(":")
                        valeur = variable_modifiee[1] + str(random.randint(int(valeur[0]),int(valeur[1])))
                        jeu[id_partie].variables["resultat"] = valeur[1:]
                    else:
                        valeur = variable_modifiee[1] + variable_modifiee[2]
                    if "+" not in valeur and "-" not in valeur:
                        jeu[id_partie].variables[variable_modifiee[0]] = int(valeur[1:])
                    else:
                        jeu[id_partie].variables[variable_modifiee[0]] = jeu[id_partie].variables[variable_modifiee[0]] + int(valeur)
                    if case_verifiee[3] != "null":
                        afficher_texte = 1
                    
                    if variable_modifiee[0].endswith("_o"):
                        if jeu[id_partie].id_scenario.startswith(url_certifiees):
                            jeu[id_partie].variables_online[jeu[id_partie].id_scenario][variable_modifiee[0]] = jeu[id_partie].variables[variable_modifiee[0]]
                            with open('variables_online.json', 'w') as var_o: 
                                json.dump(jeu[id_partie].variables_online, var_o, indent=4)

                except:
                    await ctx.send(f'```fix\nErreur [002] dans la variable {variable_modifiee[0]} et sa valeur ajoutée {element}```')
        except IndexError: 
            await ctx.send(f'```fix\nLe scénario comporte une syntaxe incorrecte : probablement une erreur dans le nombre de salles.```')
            return "break"
    if afficher_texte == 1:
        await envoyer_texte(ctx,case_verifiee[3])
    
async def verifier_cases_speciales(ctx,code="0"):
    id_partie = str(ctx.guild.id)+str(ctx.channel.id)
    for case_verifiee in jeu[id_partie].case[jeu[id_partie].emplacement]:
        if isinstance(case_verifiee,list) is False:
            pass
        elif case_verifiee[0] == "997":
            presence_reaction = 0
            for objet in case_verifiee[1]:
                if "§" in objet:
                    presence_reaction = 1
            if presence_reaction == 1:
                pass
            elif case_verifiee[1] == "null" or await condition_acces(ctx,case_verifiee[1],code) == 1:
                event = await executer_event(ctx,code,case_verifiee)
                if event == "break":
                    if id_partie in jeu:
                        jeu[id_partie].case_auto = 0
                    break
            else:
                pass
        elif case_verifiee[0] == "999" or case_verifiee[0] == "998":
            if case_verifiee[1] != "null":
                await envoyer_texte(ctx,case_verifiee[1])
            await asyncio.sleep(2)
            del jeu[id_partie]
            try: 
                voice = get(bot.voice_clients, guild=ctx.guild)
                if voice.is_playing():
                    voice.stop()
                await voice.disconnect()
            except:
                pass
            return
        else:
            pass

@bot.command(aliases=['roll', 'dice', 'dices', 'des', 'lancer_des'])        
async def jeter_des(ctx,*args):
    """j!jeter_des XdY' lance X dés de Y faces (1d6 par défaut)"""
    i = 0
    resultat = []
    temp = 0
    total = 0
    nb_reussite_total = 0
    valeur_ajoutee = 0
    choix_des = ' '.join(args)
    if choix_des == "":
        choix_des = "1d6"
    choix_des = choix_des.replace("D","d")
    choix_des = choix_des.replace(" + ","+")
    choix_des = choix_des.replace("+ ","+")
    choix_des = choix_des.replace(" +","+")
    choix_des = choix_des.replace(" ","+")
    try:
        lancer_total = choix_des.split("+")
        for element in lancer_total: #Pour chaque lancer dans la commande
            total_temp = 0
            reussite = 0
            nb_reussite = 0
            valeur_relance = 0
            valeur_ajout = 0
            if element.isdigit(): #si c'est une simple valeur, on l'ajoute
                total += int(element)
                valeur_ajoutee += int(element)
            else: #Si c'est un lancer, on le décompose
                type_actuel = element.split("d") #On sépare le nombre de dés et de faces
                nombre_des = int(type_actuel[0]) #D'abord le nombre de dés
                pos1 = type_actuel[1].find("r") # On determine si y'a un "r" et sa position => relance si valeur
                pos2 = type_actuel[1].find("m") # On determine si y'a un "m" et sa position => ajoute un dé si dé >= valeur
                pos3 = type_actuel[1].find("!") # On determine si y'a un "!" et sa position => compte réussites si valeur >= X
                if pos1 > 0: #Si y'a un "r", on recupère la valeur des dés à relancer
                    if pos2 > 0:
                        valeur_relance = int(type_actuel[1][pos1+1:pos2])
                    elif pos3 > 0:
                        valeur_relance = int(type_actuel[1][pos1+1:pos3])
                    else:
                        valeur_relance = int(type_actuel[1][pos1+1:])
                        
                if pos2 > 0: #Si y'a un "m", on récupère la valeur pour laquelle on ajoute un dé
                    if pos3 > 0:
                        valeur_ajout = int(type_actuel[1][pos2+1:pos3])
                    else:
                        valeur_ajout = int(type_actuel[1][pos2+1:])
                        
                if pos3 > 0: #si y'a un "!", on récupère la valeur à partir de laquelle on compte les réussites
                    reussite = int(type_actuel[1][pos3+1:])
                    
                if pos1 > 0:
                    nombre_face = int(type_actuel[1][:pos1])
                elif pos2 > 0:
                    nombre_face = int(type_actuel[1][:pos2])
                elif pos3 > 0:
                    nombre_face = int(type_actuel[1][:pos3])
                else:
                    nombre_face = int(type_actuel[1])

                resultat.append("D"+str(nombre_face)+" : ")
                i = 0
                while i < int(nombre_des):
                    if valeur_relance > 0:
                        while True: #Boucle qui se repete si le dé donne la valeur de relance
                            temp = random.randint(1,nombre_face)
                            if temp != valeur_relance:
                                break
                    else:
                        temp = random.randint(1,nombre_face)
                    if reussite > 0 :
                        if temp >= reussite:
                            nb_reussite += 1
                    if temp < valeur_ajout or valeur_ajout <= 0:
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
    except (ValueError, IndexError) :
        await ctx.send(f'```fix\nErreur dans les paramètres. exemple : !jeter_des 2d6  pour 2 dés de 6 faces```')
    else:
        resultat = ''.join(map(str, resultat))
        await ctx.send(f'```{resultat}```')
        
@bot.command(aliases=['coin', 'coins', 'pileface','flip','coinflip'])
async def lancer_pieces(ctx,nombre_piece: typing.Optional[int]):
    """j!lancer_pieces X' lance X pièces (1 par défaut)"""
    i = 0
    resultat = []
    try:
        nombre_piece = int(nombre_piece)
        for i in range(nombre_piece):
            if random.randint(0,1) == 0:
                resultat.append("pile")
            else:
                resultat.append("face")
            i += 1
    except:
        await ctx.send(f'```fix\nErreur dans les paramètres. !lancer_pieces[nombre de pièces]```')
    else:
        resultat = ', '.join(map(str, resultat))
        await ctx.send(f'```fix\nVous avez obtenu : {resultat}```')            

@bot.command(aliases=['play', 'load', 'jo'])  
@commands.guild_only()
@in_channel('jdr-bot')
async def jouer(ctx,nom_scenario="...") :
    """j!jouer choix' lance une partie avec le scenario \"choix\""""
    id_partie = str(ctx.guild.id)+str(ctx.channel.id)
    if id_partie in jeu:
        await ctx.send(f'```fix\nUne partie est déjà en cours```')
        return 0
    elif nom_scenario == "...":
        await ctx.send(f'```fix\nIl faut faire !jouer [nom_du_scenario], c\'est pas compliqué !```')
        return 0
    i = 0
    j = 2
    n = 0

    jeu[id_partie] = Rpg()
    # path = os.getcwd() + "\scenarios"; #pour test en local
    charger_url(ctx)
    
    try: # ouvre le scénario 
        
        if nom_scenario.lower().endswith(".txt") is False and nom_scenario.lower().startswith("http") is False:
            nom_scenario += ".txt"
        
        #à partir d'un dossier local
        # with open(os.path.join(path, nom_scenario), 'r', encoding="utf8") as data:
            # jeu[id_partie].scenario = data.readlines()
        
        # à partir d'une url  
        url_actuelle = ""
        for url in lien[id_partie].url_lien: #On vérifie si le scénario existe, url par url.
            try:
                page = requests.get(url).text
                soup = BeautifulSoup(page,'html.parser')
                liste = []
                for node in soup.find_all('a'):
                    if node.get('href').endswith('.txt'):
                        liste.append(node.get('href'))
                liste2 = [x.lower() for x in liste]
                nom_scenario_l = nom_scenario.lower()
                position = 0
                if nom_scenario_l in liste2:
                    url_actuelle = url
                    position = liste2.index(nom_scenario_l)
                    nom_scenario = liste[position]
                    break
            except: #si l'url est incorrecte, on passera à la suivante
                pass
        data = urllib.request.urlopen(url_actuelle+nom_scenario).read().decode('utf-8') # utf-8 pour remote files, ANSI pour locales files
        data = data.replace("\n","/n\n").split("\n")
        jeu[id_partie].scenario = [x.replace("/n","\n") for x in data]
        
        jeu[id_partie].id_scenario = url_actuelle+nom_scenario  #Version en ligne
        # jeu[id_partie].id_scenario = "local/" + nom_scenario  #Version en local
        
    except: # gérer l'erreur : le scénario n'a pas été trouvé sur une des url ou son nom est incorrect.
        await ctx.send(f'```fix\nLe scénario : "{nom_scenario}" n\'existe pas !```')
        del jeu[id_partie]
        return
        
    try:
        voice = get(bot.voice_clients, guild=ctx.guild)
        try:
            channel = await commands.VoiceChannelConverter().convert(ctx, str("JDR-Bot"))
            voice = await channel.connect(timeout=3, reconnect=False)
        except asyncio.TimeoutError:
            await ctx.send(f'```fix\nImpossible de rejoindre le channel vocal \'JDR-Bot\'```')
        except:
            await ctx.send(f'```fix\nImpossible de trouver le channel vocal \'JDR-Bot\'```')
        
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
        jeu[id_partie].variables_description["nb_parties_o"] = "Nombre de parties jouées"
        
        if jeu[id_partie].id_scenario.startswith(url_certifiees):
            with open('variables_online.json', 'w') as var_o: 
                json.dump(jeu[id_partie].variables_online, var_o, indent=4)
        
        jeu[id_partie].scenario = [ligne for ligne in jeu[id_partie].scenario if ligne != '\n' and ligne != '\r']
        tableau_tmp = []
        tmp = ""
        
        for ligne in jeu[id_partie].scenario: #fusionne les lignes coupé par &&, et ignore les commentaires ("##")
            ligne = ligne.replace("\n","")
            ligne = ligne.replace("\r","")
            ligne = ligne.split("##")[0]
            if ligne.endswith("&&"):
                tmp += ligne[:-2];
            else:
                if tmp != "":
                    tableau_tmp.append(tmp + ligne);
                    tmp = ""
                else:
                    tableau_tmp.append(ligne)
        jeu[id_partie].scenario = tableau_tmp

        jeu[id_partie].scenario[0] = jeu[id_partie].scenario[0].replace('\n',"")
        if "|" in jeu[id_partie].scenario[0]:
            temp = jeu[id_partie].scenario[0].split("|")
            elem = 0
            for element in temp:
                if elem == 0:
                    jeu[id_partie].scenario[0] = element.replace('+n+', '\n')
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
            
        while i < nombre_max:  #Pour chaque case du scénario
            jeu[id_partie].scenario[i+j] = jeu[id_partie].scenario[i+j].split(" ")
            jeu[id_partie].numero.append(jeu[id_partie].scenario[i+j][0])
            jeu[id_partie].salle_reaction[str(int(jeu[id_partie].numero[i])-1)] = ""
            if "§" in jeu[id_partie].scenario[i+j][1]: #Si on a ajouter une reaction au nom de salle (avec le séparateur §)
                jeu[id_partie].scenario[i+j][1] = jeu[id_partie].scenario[i+j][1].split("§") #on sépare nom et reaction
                jeu[id_partie].nom_salle.append(jeu[id_partie].scenario[i+j][1][0]) #on récupère le nom
                jeu[id_partie].salle_react.append(jeu[id_partie].scenario[i+j][1][1].replace('\n','')) #on récupère la réaction de salle
            else:
                jeu[id_partie].nom_salle.append(jeu[id_partie].scenario[i+j][1].replace('\n',''))
                jeu[id_partie].salle_react.append("...")
            j+=1
            jeu[id_partie].texte.append(jeu[id_partie].scenario[i+j])
            jeu[id_partie].texte[i] = jeu[id_partie].texte[i].rstrip().replace('+n+', '\n')
            j+=1
            if jeu[id_partie].scenario[i+j].strip() == "|":
                jeu[id_partie].objet.append(jeu[id_partie].scenario[i+j].strip())
                jeu[id_partie].nb_objets.append(0)
            else:   
                jeu[id_partie].objet.append(jeu[id_partie].scenario[i+j].strip().split("|"))
                jeu[id_partie].nb_objets.append(int(len(jeu[id_partie].objet[i])/5))
                for o in range(jeu[id_partie].nb_objets[i]):
                    if jeu[id_partie].objet[i][1+(o*5)] != "variable":
                        jeu[id_partie].objet[i][0+(o*5)] = jeu[id_partie].objet[i][0+(o*5)].lower()  #On enlève les majuscule du nom, sauf si c'est une variable
                    jeu[id_partie].objet_reaction[jeu[id_partie].objet[i][0+(o*5)]] = ""
                    if "§" in jeu[id_partie].objet[i][2+(o*5)]: #On regarde si reaction dans examiner meuble
                        jeu[id_partie].objet[i][2+(o*5)] = jeu[id_partie].objet[i][2+(o*5)].split("§")
                        jeu[id_partie].meubleex_react.append(jeu[id_partie].objet[i][2+(o*5)][1])
                        jeu[id_partie].objet_reaction[jeu[id_partie].objet[i][0+(o*5)]] += jeu[id_partie].objet[i][2+(o*5)][1]
                        jeu[id_partie].salle_reaction[str(int(jeu[id_partie].numero[i])-1)] += jeu[id_partie].objet[i][2+(o*5)][1]
                        jeu[id_partie].objet[i][2+(o*5)] = jeu[id_partie].objet[i][2+(o*5)][0]
                    else:
                        jeu[id_partie].objet[i][2+(o*5)] = jeu[id_partie].objet[i][2+(o*5)].replace('+n+', '\n') #description meuble
                        
                    if "§" in jeu[id_partie].objet[i][3+(o*5)]: #On regarde si reaction dans prendre objet
                        jeu[id_partie].objet[i][3+(o*5)] = jeu[id_partie].objet[i][3+(o*5)].split("§")
                        jeu[id_partie].objetpr_react.append(jeu[id_partie].objet[i][3+(o*5)][1])
                        jeu[id_partie].objet_reaction[jeu[id_partie].objet[i][0+(o*5)]] += jeu[id_partie].objet[i][3+(o*5)][1]
                        jeu[id_partie].salle_reaction[str(int(jeu[id_partie].numero[i])-1)] += jeu[id_partie].objet[i][3+(o*5)][1]
                        jeu[id_partie].objet[i][3+(o*5)] = jeu[id_partie].objet[i][3+(o*5)][0]
                    else:
                        jeu[id_partie].objet[i][3+(o*5)] = jeu[id_partie].objet[i][3+(o*5)].replace('+n+', '\n') #prendre objet
                        
                    if "§" in jeu[id_partie].objet[i][4+(o*5)]: #On regarde si reaction dans examiner objet
                        jeu[id_partie].objet[i][4+(o*5)] = jeu[id_partie].objet[i][4+(o*5)].split("§")
                        jeu[id_partie].objetex_react.append(jeu[id_partie].objet[i][4+(o*5)][1])
                        jeu[id_partie].objet_reaction[jeu[id_partie].objet[i][0+(o*5)]] += jeu[id_partie].objet[i][4+(o*5)][1]
                        jeu[id_partie].salle_reaction[str(int(jeu[id_partie].numero[i])-1)] += jeu[id_partie].objet[i][4+(o*5)][1]
                        jeu[id_partie].objet[i][4+(o*5)] = jeu[id_partie].objet[i][4+(o*5)][0]
                    else:
                        jeu[id_partie].objet[i][4+(o*5)] = jeu[id_partie].objet[i][4+(o*5)].replace('+n+', '\n') #description objet

                    if jeu[id_partie].objet[i][1+(o*5)] == "variable":
                        jeu[id_partie].variables[jeu[id_partie].objet[i][0+(o*5)]] = 0
                        jeu[id_partie].variables_description[jeu[id_partie].objet[i][0+(o*5)]] = lire_variable(ctx, jeu[id_partie].objet[i][4+(o*5)])
                    else:
                        jeu[id_partie].description[jeu[id_partie].objet[i][0+(o*5)]] = jeu[id_partie].objet[i][4+(o*5)]
                        
                    jeu[id_partie].objet_reaction[jeu[id_partie].objet[i][0+(o*5)]] = tuple(jeu[id_partie].objet_reaction[jeu[id_partie].objet[i][0+(o*5)]])
            j+=1
            direction=[]
            
            while "*****" not in jeu[id_partie].scenario[i+j]:  #Pour chaque salle explorable à partir de l'emplacement.
                ligne = jeu[id_partie].scenario[i+j].replace("+n+","\n")
                reaction_event = 0
                if "|" not in ligne:
                    direction.append(ligne)
                else:
                    ligne = ligne.split("|")
                    if ligne[0] not in ("998","999"):
                        ligne[1] = ligne[1].split(" ")
                        emoji = deepcopy(ligne)
                        for objet in emoji[1]:
                            if "§" in objet:
                                jeu[id_partie].salle_reaction[str(int(jeu[id_partie].numero[i])-1)] += objet.split("§")[1]
                                if ":" not in emoji[0]:
                                    emoji[0] = int(objet.split("§")[0])
                                    emoji[1].append(objet.split("§")[1])
                                    emoji[1].remove(objet)
                                    reaction_event = 1
                                else: #+numéro de salle pour les actions locales
                                    jeu[id_partie].action_reaction[emoji[0]+":"+str(i+1)] = objet.split("§")[1]
                                    jeu[id_partie].action_reaction_inv[objet.split("§")[1]] = emoji[0] + ":" + str(i+1)
                        if reaction_event == 1:
                            jeu[id_partie].event_react.append(emoji)        
                    direction.append(ligne)
                j+=1

            jeu[id_partie].case.append(direction)
            jeu[id_partie].salle_reaction[str(int(jeu[id_partie].numero[i])-1)] = list(jeu[id_partie].salle_reaction[str(int(jeu[id_partie].numero[i])-1)])
            i+=1
        case_actuelle = i+j
        
        for ligne in range(case_actuelle,len(jeu[id_partie].scenario)): #Pour chaque ligne après la dernière salle
            ligne_actuelle = jeu[id_partie].scenario[ligne]
            # On regarde le premier élément d'une ligne pour déterminer son utilité
            if ":" in ligne_actuelle.split("|")[0]: #Action custom
                ligne_actuelle = ligne_actuelle.split("|")
                ligne_actuelle[1] = ligne_actuelle[1].split(" ")
                for element in ligne_actuelle[1]:
                    if element.startswith("§"): #"+all" pour les action globales
                        jeu[id_partie].action_reaction[ligne_actuelle[0]+":"+"all"] = element[1:]
                        jeu[id_partie].action_reaction_inv[element[1:]] = ligne_actuelle[0] + ":" + "all"
                jeu[id_partie].action_custom.append(ligne_actuelle)
            
            elif "§" in ligne_actuelle.split("|")[0]: # Alias des réactions
                alias_react = jeu[id_partie].scenario[ligne].split("|")
                for element in alias_react:
                    if '§' in element:                                                                 
                        element = element.split("§")
                        jeu[id_partie].alias_reaction[element[0]] = element[1]
                        jeu[id_partie].alias_reaction_inv[element[1]] = element[0]
            
            elif "_o" in ligne_actuelle.split("|")[0]: #Variables_online (variable_o)
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
                        jeu[id_partie].variables[var_onl[0]] = str(var_onl[1])
                jeu[id_partie].variables_description[var_onl[0]] = var_onl[2]
        
        if jeu[id_partie].id_scenario.startswith(url_certifiees):
            with open('variables_online.json', 'w') as var_o: 
                json.dump(jeu[id_partie].variables_online, var_o, indent=4)
                
        jeu[id_partie].nom_salle = [x.lower() for x in jeu[id_partie].nom_salle]
        
        await envoyer_texte(ctx, jeu[id_partie].scenario[0])    
        if jeu[id_partie].scenario[3] != "null":
            await envoyer_texte(ctx, jeu[id_partie].scenario[3],avec_reaction="ok")
        
        await verifier_objets(ctx) #regarder si il y a des objets/conditions invisibles ou des variables
        
        await verifier_cases_speciales(ctx) #vérifier si il y a des cases spéciales
        i = 0
    except:
        await ctx.send(f'```fix\nLe scénario : "{nom_scenario}" comporte une syntaxe incorrecte au chapitre {int(i)+1}, près de la ligne {int(i+j+1)}```')
        del jeu[id_partie]
        try: 
            voice = get(bot.voice_clients, guild=ctx.guild)
            if voice.is_playing():
                voice.stop()
            await voice.disconnect()
        except:
            pass

@bot.command(aliases=['av', 'move', 'go'])
@commands.guild_only()  
@in_channel('jdr-bot')
async def avancer(ctx,choix="...",code="0") : 
    """j!avancer X Y' avance dans la pièce X avec le code Y (si y'a un code)"""
    id_partie = str(ctx.guild.id)+str(ctx.channel.id)
    if id_partie not in jeu:
        await ctx.send(f'```fix\nAucune partie en cours !```')
        return
    if choix == "...":
        await ctx.send(f'```fix\nJe ne peux pas deviner où tu veux aller ... fait !avancer [numéro_ou_tu_vas] voyons !```')
        return
    if choix == "0":
        choix = str(jeu[id_partie].emplacement_precedent+1)
    choix = str(choix).lower()
    test = 0
    if choix in jeu[id_partie].options.keys():
        if choix != str(jeu[id_partie].emplacement+1)  and choix != jeu[id_partie].nom_salle[jeu[id_partie].emplacement]:
            test = 1
    if choix in jeu[id_partie].nom_salle:
        choix = jeu[id_partie].nom_salle.index(choix)
        choix = str(int(choix)+1)
    
    try:
        i = 0
        j = 0
        test_condition = 0
        case_testee = 0
        if test == 0:
            for case in jeu[id_partie].case[jeu[id_partie].emplacement]:
                if isinstance(case,list) is False and choix != "997" and choix.startswith("action:") is False:   # Si la case contient juste un chiffre (= numero de salle) ou "retour"
                    if "->" in case:
                        if choix == case.split("->")[0]:
                            choix = case.split("->")[1]
                            test = 1
                            test_condition = 0
                            break
                    elif (case != "precedent" and choix == case) or (case == "precedent" and choix == str(jeu[id_partie].emplacement_precedent+1)): #On vérifie si c'est le numéro de salle choisis
                        test = 1
                        test_condition = 0
                        break
                elif isinstance(case,list) and choix != "997" and choix.startswith("action:") is False:    #autre si choix = numero
                    if "->" in case[0]:
                        if choix == case[0].split("->")[0]:
                            test = await condition_acces(ctx,case[1],code)
                            test_condition = 1
                            case_testee = i
                            if test == 1:
                                choix = case[0].split("->")[1]
                                break     
                    else:
                        if (case[0] != "precedent" and choix == case[0]) or (case[0] == "precedent" and choix == str(jeu[id_partie].emplacement_precedent+1)):
                            test = await condition_acces(ctx,case[1],code)
                            test_condition = 1
                            case_testee = i
                            if test == 1:
                                break
                i += 1
        if test == 2:
            if jeu[id_partie].case[jeu[id_partie].emplacement][case_testee][2] != "null":
                await envoyer_texte(ctx,jeu[id_partie].case[jeu[id_partie].emplacement][case_testee][2])
        if test == 1:
            if test_condition == 1:
                if jeu[id_partie].case[jeu[id_partie].emplacement][case_testee][3] != "null":
                    await envoyer_texte(ctx,jeu[id_partie].case[jeu[id_partie].emplacement][case_testee][3])
                if "$" in jeu[id_partie].case[jeu[id_partie].emplacement][case_testee][1]:
                        jeu[id_partie].case[jeu[id_partie].emplacement][case_testee] = jeu[id_partie].case[jeu[id_partie].emplacement][case_testee][0]
                        
            try:
                jeu[id_partie].variables["valeur"] = int(code)
                jeu[id_partie].emplacement_precedent = jeu[id_partie].emplacement
                jeu[id_partie].emplacement = int(choix)-1
                if jeu[id_partie].texte[jeu[id_partie].emplacement] != "null":
                    await envoyer_texte(ctx,jeu[id_partie].texte[jeu[id_partie].emplacement],avec_reaction="ok")
                await verifier_objets(ctx) #regarder si il y a des objets/conditions invisibles ou des variables
                await verifier_cases_speciales(ctx,code)
            except ValueError: 
                await ctx.send(f'```fix\nWarning : !Avancer [numéro] (valeur) : {code} n\'est pas une valeur numérique.```')
            
            
        elif test != 2:
            await ctx.send(f'```fix\nChoix impossible !```')
    except IndexError:
        await ctx.send(f'```fix\nLe scénario comporte une syntaxe incorrecte (probablement nombre de salles incorrect)```')
    except:
        pass #Arrive lorsque le scénario ou discord envoie une redirection après la fermeture du scénario (= keyerror)

@bot.command(aliases=['back', 'return'])
@commands.guild_only()  
@in_channel('jdr-bot')
async def reculer(ctx,code="0") :
    id_partie = str(ctx.guild.id)+str(ctx.channel.id)
    await avancer(ctx,str(jeu[id_partie].emplacement_precedent+1),code)

@bot.command(aliases=['pr', 'take'])
@commands.guild_only()
@in_channel('jdr-bot')
async def prendre(ctx,objet_cible="...",par_reponse=0) :
    """j!prendre X' prend l'objet X"""
    id_partie = str(ctx.guild.id)+str(ctx.channel.id)
    objet_cible = objet_cible.lower()
    i = 0
    try :
        for o in range(jeu[id_partie].nb_objets[jeu[id_partie].emplacement]):
            if objet_cible == jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)]: #si cible = un des objets de la pièce, cible2 = "test1" (objet) et i = n° de l'objet
                i = o
                break
        if objet_cible == jeu[id_partie].objet[jeu[id_partie].emplacement][0+(i*5)] and objet_cible != "null":
            if jeu[id_partie].objet[jeu[id_partie].emplacement][1+(i*5)] == "invisible" or jeu[id_partie].objet[jeu[id_partie].emplacement][1+(i*5)] == "variable":
                await ctx.send(f'```fix\nCe n\'est pas un objet à prendre```')
            elif jeu[id_partie].objet[jeu[id_partie].emplacement][0+(i*5)] != "|" and jeu[id_partie].objet[jeu[id_partie].emplacement][0+(i*5)] not in jeu[id_partie].inventaire_en_cours:
                jeu[id_partie].inventaire_en_cours.append(jeu[id_partie].objet[jeu[id_partie].emplacement][0+(i*5)])
                jeu[id_partie].objet[jeu[id_partie].emplacement][0+(i*5)] = "null"
                if jeu[id_partie].objet[jeu[id_partie].emplacement][3+(i*5)] != "null":
                    await envoyer_texte(ctx,jeu[id_partie].objet[jeu[id_partie].emplacement][3+(i*5)])
                if objet_cible in jeu[id_partie].objet_reaction.keys():
                    try:
                        for element in jeu[id_partie].objet_reaction[objet_cible]:
                            jeu[id_partie].salle_reaction[str(jeu[id_partie].emplacement)].remove(element)
                    except:
                        pass    
                                
                await verifier_cases_speciales(ctx,code="0") #prendre un objet reverifie et redéclenche les 997 comme lors de l'entrée dans une salle.

            else:
                await ctx.send(f'```fix\nVous possédez déjà l\'objet \"{objet_cible}\".```')
        elif objet_cible == "...":
            await ctx.send(f'```fix\nIl faut préciser ce que tu veux prendre : !prendre [nom_de_l\'objet]```')
        else:
            if par_reponse == 0:
                await ctx.send(f'```fix\nIl n\'y a pas de \"{objet_cible}\"```')
            else:
                await ctx.send(f'```fix\nLa réponse \"{objet_cible}\" est incorrecte.```')
    except:
        await ctx.send(f'```fix\nIl n\'y a pas de scénario en cours ou le scénario comporte une erreur.```')
        

@bot.command(aliases=['ex', 'look','inspect','inspecter'])
@commands.guild_only()          
@in_channel('jdr-bot')
async def examiner(ctx,cible="ici") :
    """j!examiner [element]' examine l'élément (endroit de la pièce, objet de la pièece ou de l'inventaire, etc.). Par défaut : examine la pièce où on se trouve."""
    id_partie = str(ctx.guild.id)+str(ctx.channel.id)
    i = 0
    cible2 = ""
    cible = cible.lower()
    try:
        for o in range(jeu[id_partie].nb_objets[jeu[id_partie].emplacement]):
            if cible == jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)]: #si cible = un des objets de la pièce, cible2 = "objet" et i = n° de l'objet
                cible2 = "objet"
                i = o
                break
            elif cible == jeu[id_partie].objet[jeu[id_partie].emplacement][1+(o*5)] and jeu[id_partie].objet[jeu[id_partie].emplacement][0+(o*5)] != "null" : #si cible = un des meubles de la pièce, cible2 = "meuble" et i = n° de l'objet
                cible2 = "meuble"
                i = o
                break

        if cible == "ici":
            await envoyer_texte(ctx, jeu[id_partie].texte[jeu[id_partie].emplacement],avec_reaction="ok") 
        elif cible == "invisible" or cible == "variable" or cible[0] == "-" or cible == "null":
            await ctx.send(f'```fix\nC\'est impossible !```')
        elif cible in jeu[id_partie].variables:
            if cible.endswith("_s") is False or cible == "resultat":
                await ctx.send(f'```fix\n{cible} : {jeu[id_partie].variables[cible]}```')
            await envoyer_texte(ctx,jeu[id_partie].variables_description[cible])
        elif cible in jeu[id_partie].variables_texte:
            await envoyer_texte(ctx,jeu[id_partie].variables_texte[cible])
            await envoyer_texte(ctx,jeu[id_partie].variables_description[cible])
        elif cible in jeu[id_partie].inventaire_en_cours or cible in jeu[id_partie].inventaire_invisible or cible2 == "objet":
            await envoyer_texte(ctx,jeu[id_partie].description[cible])
        elif jeu[id_partie].objet[jeu[id_partie].emplacement][0+(i*5)] != "|":
            if cible2 == "meuble" :
                if jeu[id_partie].objet[jeu[id_partie].emplacement][0+(i*5)] not in jeu[id_partie].inventaire_en_cours:
                    await envoyer_texte(ctx,jeu[id_partie].objet[jeu[id_partie].emplacement][2+(i*5)])
                else:
                    await ctx.send(f'```fix\nIl n\'y a plus rien d\'intéressant ici pour l\'instant ...```')
            else: 
                await ctx.send(f'```fix\nJe ne comprend pas ce que vous voulez examiner.```')
        else:
            await ctx.send(f'```fix\nJe ne comprend pas ce que vous voulez examiner.```')
    except:
        await ctx.send(f'```fix\nIl n\'y a pas de scénario en cours ou le scénario comporte une erreur.!```')
        

@bot.command(aliases=['modif', 'edit', 'change','changer'])
@commands.guild_only()
@in_channel('jdr-bot')
async def modifier(ctx, variable="...", valeur=0):
    """Affiche l'inventaire du joueur"""
    id_partie = str(ctx.guild.id)+str(ctx.channel.id)
    try:
        if id_partie in jeu:
            if variable == "...":
                await ctx.send(f'```fix\nIl y a un souci dans vos arguments de commande. La commande est \'j!modifier nom_variable valeur\'```')
            elif variable in jeu[id_partie].variables:
                if variable.endswith("_m"):
                    jeu[id_partie].variables[variable] = int(valeur)
                    await ctx.send(f'```fix\nC\'est noté, {variable} = {valeur}.```')
                    
                    await verifier_cases_speciales(ctx,code="0") #modifier une variable reverifie et redéclenche les 997 comme lors de l'entrée dans une salle.
                                    
                else:
                    await ctx.send(f'```fix\nCette variable n\'est pas modifiable manuellement.```')
            else:
                await ctx.send(f'```fix\nCette variable est inconnue.```')
        else:
            await ctx.send(f'```fix\nIl n\'y a pas de partie en cours !```')
    except:
        await ctx.send(f'```fix\nIl y a un souci dans vos arguments de commande. La commande est \'j!modifier nom_variable valeur\'```')

@bot.command(aliases=['repondre', 'répondre', 'réponse', 'reply','answer'])
@commands.guild_only()
@in_channel('jdr-bot')
async def reponse(ctx, valeur="..."):
    id_partie = str(ctx.guild.id)+str(ctx.channel.id)
    if id_partie not in jeu: 
        await ctx.send(f'```fix\nAucune partie en cours !```')
        return
    variable_texte = ""
    for i in range(jeu[id_partie].nb_objets[jeu[id_partie].emplacement]):
        if jeu[id_partie].objet[jeu[id_partie].emplacement][i*5+1] == "variable_t":
            variable_texte = jeu[id_partie].objet[jeu[id_partie].emplacement][i*5]
            var = i
    if valeur == "...":
        await envoyer_texte(ctx,'Veuillez indiquer une réponse : "[[PREFIX]]reponse votre_reponse"')
    elif variable_texte != "":
        jeu[id_partie].variables_texte[variable_texte] = valeur
        
        if variable_texte.endswith("_o"):
            jeu[id_partie].variables_online[jeu[id_partie].id_scenario][variable_texte] = jeu[id_partie].variables_texte[variable_texte]
            with open('variables_online.json', 'w') as var_o: 
                json.dump(jeu[id_partie].variables_online, var_o, indent=4)
        
        await envoyer_texte(ctx,jeu[id_partie].objet[jeu[id_partie].emplacement][var*5+3])
        await verifier_cases_speciales(ctx,code="0")
    else:
        try:
            jeu[id_partie].variables["reponse"] = int(valeur)
            await verifier_cases_speciales(ctx,code="0")
        except:
            await prendre(ctx, str(valeur), 1)

        
@bot.command(aliases=['sc', 'loaded'])
@commands.guild_only()          
@in_channel('jdr-bot')
async def scenario_en_cours(ctx):
    """Affiche le scenario en cours"""
    id_partie = str(ctx.guild.id)+str(ctx.channel.id)
    try:
        await ctx.send(f'```fix\nLe scénario : \"{jeu[id_partie].scenario[0]}\" est en cours.```')
    except:
        await ctx.send(f'```fix\nIl n\'y a pas de scénario en cours !```')
        
@bot.command(aliases=['iv', 'item', 'items'])
@commands.guild_only()
@in_channel('jdr-bot')
async def inventaire(ctx):
    """Affiche l'inventaire du joueur"""
    id_partie = str(ctx.guild.id)+str(ctx.channel.id)
    if id_partie in jeu:
        embed=discord.Embed(color=0x17B93C ,title="**Inventaire**", description="Votre inventaire contient : ")
        for objet in jeu[id_partie].inventaire_en_cours:
            embed.add_field(name=objet, value=jeu[id_partie].description[objet], inline=False)
        message = await ctx.send(embed=embed)
        for element in jeu[id_partie].options:
            try:
                await message.add_reaction(jeu[id_partie].options[element])
            except: 
                pass #dans le cas où la réaction n'existe pas dans le scénario, suite à une erreur de l'auteur, le bot doit ignoré
    else:
        await ctx.send(f'```fix\nIl n\'y a pas de partie en cours !```')

@bot.command(aliases=['je', 'throw'])
@commands.guild_only()
@in_channel('jdr-bot')     
async def jeter(ctx,objet_jeter="???"):
    """jette un objet par terre"""
    id_partie = str(ctx.guild.id)+str(ctx.channel.id)
    if id_partie in jeu:
        if objet_jeter == "???":
            await ctx.send(f'```fix\nChoisissez un objet à jeter : !jeter [objet]```')
        elif objet_jeter in jeu[id_partie].inventaire_en_cours:
            jeu[id_partie].inventaire_en_cours.remove(objet_jeter)
            await ctx.send(f'```fix\nVous vous débarassez de \"{objet_jeter}\"```')
        else:
            await ctx.send(f'```fix\nVous n\'avez pas \"{objet_jeter}\" dans votre inventaire.```')
    else:
        await ctx.send(f'```fix\nIl n\'y a pas de partie en cours !```')

@bot.command(aliases=['act', 'faire'])
@commands.guild_only()
@in_channel('jdr-bot')     
async def action(ctx,choix = "...", cible = "..."):
    """action personnalisée"""
    id_partie = str(ctx.guild.id)+str(ctx.channel.id)
    try:
        test = 0
        texte = ""
        action_trouvee = 0
        if choix == "..." or cible == "...":
            await ctx.send(f'```fix\nPrécisez l\'action et la cible```')
        else: #On verifie d'abord les actions locales
            jeu[id_partie].variables_texte["action_cible"] = cible
            for case_verifiee in jeu[id_partie].case[jeu[id_partie].emplacement]:
                if isinstance(case_verifiee,list) is True:
                    if ":" in case_verifiee[0]:
                        if choix == case_verifiee[0].split(":")[0] and \
                        (cible == case_verifiee[0].split(":")[1] or case_verifiee[0].split(":")[1] == "all"):
                            jeu[id_partie].variables_texte["action_cible_ok"] = cible
                            test = await condition_acces(ctx,case_verifiee[1],0)
                            action_trouvee = 1
                            texte = case_verifiee[4]
                            if test == 1:
                                await executer_event(ctx,0,case_verifiee)
                                break
            if test != 1: #Ensuite les actions globales
                for element in jeu[id_partie].action_custom:
                    if choix == element[0].split(":")[0] and \
                    (cible == element[0].split(":")[1] or element[0].split(":")[1] == "all"):
                        jeu[id_partie].variables_texte["action_cible_ok"] = cible
                        test = await condition_acces(ctx,element[1],0)
                        action_trouvee = 1
                        texte = element[4]
                        if test == 1:
                            await executer_event(ctx,0,element)
                            break
            if action_trouvee == 1 and test != 1 and texte != "null":
                await envoyer_texte(ctx,texte)
        if action_trouvee == 0 and choix != "..." and cible != "...":
            await ctx.send(f'```fix\nIntéressant ... mais impossible !```')
    except:
        pass


@bot.command(aliases=['ab', 'giveup'])
@commands.guild_only()
@in_channel('jdr-bot')
async def abandonner(ctx):
    """Met fin à la partie par un abandon"""
    id_partie = str(ctx.guild.id)+str(ctx.channel.id)
    if id_partie not in jeu:
        await ctx.send(f'```fix\nAucune partie en cours```')
        return
    await ctx.send(f'```fix\nVous abandonnez la partie ! C\'est lâche !!!```')
    del jeu[id_partie]
    try: 
        voice = get(bot.voice_clients, guild=ctx.guild)
        if voice.is_playing():
            voice.stop()
        await voice.disconnect()
    except:
        pass

# @bot.command()  #Commande modifiable pour tout type de tests pendant le dev
# @commands.guild_only()   
# @in_channel('jdr-bot')
# async def debug(ctx,texte=""):
    # """Information de debug"""
    # id_partie = str(ctx.guild.id)+str(ctx.channel.id)
    # texte = texte.replace('+n','\n')
    # await ctx.send(f'```\n{texte}```')
    #inventaire_invisible_bis = ', '.join(map(str, jeu[id_partie].inventaire_invisible))
    #if id_partie in jeu:
    #    await ctx.send(f'```fix\n{jeu[id_partie].variables} ET {jeu[id_partie].variables_description}```')
    #else:
    #    await ctx.send(f'```fix\nIl n\'y a pas de partie en cours !```')

@bot.command(aliases=['info','information','infos','documentation', 'doc', 'aide','botinfo','help'])
async def faq(ctx):
    """information sur le bot et son auteur"""
    current_time = time.time()
    difference = int(round(current_time - start_time))
    text = str(datetime.timedelta(seconds=difference))
    
    with open('prefixes.json', 'r') as f: 
        prefixes = json.load(f)
    
    embed=discord.Embed(color=0x29d9e2 ,title="**JDR-Bot**", description="JDR-Bot vous permet de jouer à différents jeux (ou scénarios), de type Jeux de rôle, Histoires dont vous êtes le héros, Escape Game, JDR textuel (façon Colossal Cave).")
    embed.set_author(name=bot.user.name+"#"+bot.user.discriminator, icon_url=bot.user.avatar_url)
    embed.set_thumbnail(url=bot.user.avatar_url)
    embed.add_field(name="**Auteur**", value="<@"+str(My_ID)+">", inline=True)
    embed.add_field(name="**Serveurs**", value=str(len(bot.guilds)), inline=True)
    embed.add_field(name="**Uptime**", value=text, inline=True)
    embed.add_field(name="**Comment jouer**", value="`"+prefixes[str(ctx.guild.id)][0]+"jouer scenario`", inline=True)
    embed.add_field(name="**Scénarios existant**", value="`"+prefixes[str(ctx.guild.id)][0]+"liste_scenarios`", inline=True)
    embed.add_field(name="**Ecrire un scénario**", value="Voir [Documentation](http://cyril-fiesta.fr/jdr-bot/Documentation-JDR-Bot.pdf)", inline=True)
    embed.add_field(name="**Liste détaillée des commandes**", value="Vous trouverez la liste détaillée des commandes et leurs définitions dans la [Documentation](http://cyril-fiesta.fr/jdr-bot/Documentation-JDR-Bot.pdf)", inline=False)
    embed.add_field(name="**Links**", value="[Github](https://github.com/Cyril-Fiesta/jdr-bot) | [Documentation](http://cyril-fiesta.fr/jdr-bot/Documentation-JDR-Bot.pdf) | [Invitation](https://discord.com/oauth2/authorize?client_id=521137132857982976&permissions=70671424&scope=bot) | [Discord officiel](https://discord.com/invite/Z63DtVV)", inline=False)
    embed.add_field(name="**Rejoignez-nous**", value="N'hésitez pas à nous rejoindre sur le discord [Make&Play](https://discord.com/invite/Z63DtVV), spécial Créateur en tout genre et Gamers ;)", inline=False)
    await ctx.send(embed=embed)

@bot.command(aliases=['statistique', 'stats','stat'])
@commands.guild_only()
@in_channel('jdr-bot')
async def statistiques(ctx, lien_scenario = "..."):
    with open('variables_online.json', 'r') as var_o: 
        statistique_online = json.load(var_o)
        
    with open('prefixes.json', 'r') as f: 
        prefixes = json.load(f)
        
    nb_parties = 0
    lien_scenario = lien_scenario.lower()
    if lien_scenario != "...":
        if lien_scenario.endswith("/") is True:
            lien_scenario -= "/"
        if lien_scenario.endswith(".txt") is False:
            lien_scenario += ".txt"
        if lien_scenario.startswith("http") is False: #Sans url, on essaye sur celle par défaut
            lien_scenario = "http://cyril-fiesta.fr/jdr-bot/scenarios/" + lien_scenario

    if lien_scenario == "...":
        for element in statistique_online:
            nb_parties += statistique_online[element]["nb_parties_o"]
        embed=discord.Embed(color=0xfe1b00 ,title="**JDR-Bot Statisques**", description="Statistiques générales de JDR-Bot")
        embed.add_field(name="**Nombre de parties jouées depuis la version 1.6**", value=f'{nb_parties} parties', inline=False)
        embed.add_field(name="**Connaître le nombre de parties par scénario :**", value=f'Utilisez la commande `{prefixes[str(ctx.guild.id)][0]}statistiques lien_du_scenario`\nPar exemple `{prefixes[str(ctx.guild.id)][0]}statistiques https://cyril-fiesta.fr/jdr-bot/scenarios/chateau.txt`', inline=False)
    elif lien_scenario in statistique_online:
        embed=discord.Embed(color=0xfe1b00 ,title="**JDR-Bot Statisques**", description=f'Statistiques de {lien_scenario}')
        embed.add_field(name=f'**Nombre de parties jouées depuis la version 1.6**', value=f'{statistique_online[lien_scenario]["nb_parties_o"]} parties', inline=False)
    else:
        embed=discord.Embed(color=0xfe1b00 ,title="**JDR-Bot Statisques**", description="Lien de scénario incorrect, scénario n\'ayant pas encore été joué ou scénario ne se trouvant pas sur une des urls certifiées pour les variables onlines du bot.")
    
    embed.set_author(name=bot.user.name+"#"+bot.user.discriminator, icon_url=bot.user.avatar_url)
    embed.set_thumbnail(url=bot.user.avatar_url)
    await ctx.send(embed=embed)
    
#bot.loop.create_task(list_servers())
bot.run(TOKEN)
