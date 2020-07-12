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

base_url = "http://cyril-fiesta.fr/jdr-bot/scenarios/"
start_time = time.time()
categories_scenarios = {"📖" : "fiction","🔐" : "escape-game","👩‍🏫" : "tutoriel","🧩" : "exemple","🎮" : "divers"}

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
        self.variables_description = {"resultat" : "Résultat de ... quelque chose !", "valeur" : "Valeur de ... quelque chose !", "reponse" : "Réponse à une question ..."}
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
        self.last_reaction = ""
#jeu[ctx.guild.id].variable

lien = {}
class Url:
    def __init__(self):
        self.url_lien = []
#lien[ctx.guild.id].variable


@bot.event
async def on_ready():
    activity = discord.Game(name="JDR-Bot, le JDR textuel sur discord !")
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
        
        if i == 0:
            servers_list = element.name
            i = 1
        else:
            servers_list += " | " + element.name
    print('Active servers: ' + servers_list)

@bot.event
async def on_guild_join(guild):
    with open('prefixes.json', 'r') as f: 
        prefixes = json.load(f)
    
    prefixes[str(guild.id)] = ("j!","J!")
    
    with open('prefixes.json', 'w') as f: 
        json.dump(prefixes, f, indent=4)

@bot.event
async def on_guild_remove(guild):
    with open('prefixes.json', 'r') as f: 
        prefixes = json.load(f)
    
    prefixes.pop(str(guild.id))
    
    with open('prefixes.json', 'w') as f: 
        json.dump(prefixes, f, indent=4)

@bot.event
async def on_reaction_add(reaction, user):
    ctx = await bot.get_context(reaction.message)
    if str(user) == "JDR-Bot#5773":
        pass
    elif reaction.message.guild.id not in jeu and "jdr-bot" in reaction.message.channel.name and reaction.emoji in categories_scenarios:
        await liste_scenarios(ctx,categories_scenarios[reaction.emoji])
    elif reaction.message.guild.id in jeu:
        try : #Si l'objet est déjà pris on aura un ValueError si on examine le meuble.
            if reaction.emoji in jeu[ctx.guild.id].options_inv:
                if jeu[ctx.guild.id].options_inv[reaction.emoji] == "rafraichir":
                    await examiner(ctx)
                elif jeu[ctx.guild.id].options_inv[reaction.emoji] == "inventaire":
                    await inventaire(ctx)
                    
            elif reaction.emoji in jeu[reaction.message.guild.id].salle_react:
                await avancer(ctx,str(jeu[reaction.message.guild.id].salle_react.index(reaction.emoji)+1),0)
            
            elif reaction.emoji in jeu[reaction.message.guild.id].alias_reaction.values():
                await avancer(ctx,jeu[reaction.message.guild.id].alias_reaction_inv[reaction.emoji],0)
            
            else:
                for cle in jeu[reaction.message.guild.id].objet_reaction:
                    if reaction.emoji in jeu[reaction.message.guild.id].objet_reaction[cle]:
                        objet = cle
                        if objet in jeu[ctx.guild.id].objet[jeu[reaction.message.guild.id].emplacement]:
                            meuble = jeu[ctx.guild.id].objet[jeu[reaction.message.guild.id].emplacement].index(objet) + 1
                        else:
                            meuble = "???"
                        break
                if reaction.emoji in jeu[reaction.message.guild.id].meubleex_react and reaction.emoji in jeu[reaction.message.guild.id].salle_reaction[str(jeu[reaction.message.guild.id].emplacement)]:
                    if isinstance(meuble,int):
                        await examiner(ctx, jeu[ctx.guild.id].objet[jeu[reaction.message.guild.id].emplacement][meuble])
                    else:
                        await examiner(ctx,"objet_inconnu...")
                elif reaction.emoji in jeu[reaction.message.guild.id].objetex_react and reaction.emoji in jeu[reaction.message.guild.id].salle_reaction[str(jeu[reaction.message.guild.id].emplacement)]:
                    await examiner(ctx, objet)
                
                elif reaction.emoji in jeu[reaction.message.guild.id].objetpr_react and reaction.emoji in jeu[reaction.message.guild.id].salle_reaction[str(jeu[reaction.message.guild.id].emplacement)]:
                    await prendre(ctx, objet)
                        
                elif reaction.emoji in jeu[reaction.message.guild.id].salle_reaction[str(jeu[reaction.message.guild.id].emplacement)]:
                    i = 0
                    for element in jeu[reaction.message.guild.id].event_react:
                        if reaction.emoji in element[1]:
                            verification = []
                            for objet in element[1]:
                                verification.append(objet)
                            pos = verification.index(reaction.emoji)
                            verification[pos] = "§"
                            if await condition_acces(ctx,verification,code="0") == 1 and element[0] > 0:
                                await executer_event(ctx,0,element)
                                jeu[reaction.message.guild.id].event_react[i][0] -= 1
                            else:
                                if element[4] != "null":
                                    await envoyer_texte(ctx,element[4])
                            break
                        i += 1
                        
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
        
        ignored = (commands.CommandNotFound,commands.errors.UnexpectedQuoteError,commands.errors.ExpectedClosingQuoteError, commands.UserInputError, IndexError, KeyError, discord.errors.Forbidden)
        
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
            for channel in element.channels:
                if str(channel.type) == "voice":
                    pass
                elif "jdr-bot" in str(channel):
                    await channel.send(embed=embed)
    else:
        pass

def charger_url(ctx): #On charge les url de base et de la description.
    global base_url
    
    if ctx.guild.id not in lien:
        lien[ctx.guild.id] = Url()
   
    if base_url not in lien[ctx.guild.id].url_lien:
        lien[ctx.guild.id].url_lien.append(base_url)
        
    try:
        topic = ctx.message.channel.topic.replace('\n',' ').lower().split(" ")
        for element in topic:
            url = ""
            if element.startswith("http:"):
                url = element
                if url.endswith("/") is False:
                    url += "/"
                if url not in lien[ctx.guild.id].url_lien:
                    lien[ctx.guild.id].url_lien.append(url)
    except:
        pass

@bot.command(aliases=['url', 'lien', 'link'])
@commands.guild_only()
@in_channel('jdr-bot')
async def lien_jdr(ctx,action = "...", lien_scenarios = "..."): 
    """Affiche ou Modifie l'url où se trouve les scénarios."""
    global base_url
    charger_url(ctx)
    
    lien_scenarios = lien_scenarios.lower()
    if lien_scenarios.endswith("/") is False:
        lien_scenarios += "/"
    authorperms = ctx.author.permissions_in(ctx.channel)
    
    if action == "..." or action == "liste" or action == "list" or authorperms.manage_channels is False:
        liste_url = []
        liste_url.append("Liste d\'url de scénarios :\n")
        for element in lien[ctx.guild.id].url_lien:
            liste_url.append(str(element)+"\n")
        liste = ''.join(liste_url)
        await ctx.send(f'```fix\n{liste}```')
    elif action == "default" or action == "base" or action == "reset":
        lien[ctx.guild.id].url_lien = [base_url]
        await ctx.send(f'```fix\nL\'url des scénarios est désormais : {lien[ctx.guild.id].url_lien[0]}```')
    elif action == "add" or action == "ajouter":
        if lien_scenarios.startswith("http"):
            if lien_scenarios not in lien[ctx.guild.id].url_lien:
                lien[ctx.guild.id].url_lien.append(lien_scenarios)
                await ctx.send(f'```fix\nL\'url est ajoutée à JDR-Bot.```')
            else:
                await ctx.send(f'```fix\nL\'url est déjà prise en compte par JDR-Bot.```')
        else:
            await ctx.send(f'```fix\nMerci d\'indiquer une url correcte.```')
    elif action == "retirer" or action == "remove":
        if lien_scenarios in lien[ctx.guild.id].url_lien:
            lien[ctx.guild.id].url_lien.remove(lien_scenarios)
            await ctx.send(f'```fix\nL\'url est retirée de JDR-Bot.```')
        else:
            await ctx.send(f'```fix\nCette url n\'est pas présente dans JDR-Bot.```')
    else :
        await ctx.send(f'```fix\n Merci de spécifier une action correcte ("ajouter", "base", "liste" ou "retirer")```')

@bot.command(aliases=['scenario', 'scenarios','script','scripts','list_scripts'])
@commands.guild_only()
@in_channel('jdr-bot')
async def liste_scenarios(ctx,categorie="base"):
    with open('prefixes.json', 'r') as f: 
        prefixes = json.load(f)
        
    charger_url(ctx)
    for url in lien[ctx.guild.id].url_lien:
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
                        embed.add_field(name="Escape-game 🔐", value="Escape-game, scénarios à énirgmes, etc.", inline=False)
                        embed.add_field(name="Tutoriel 👩‍🏫", value="Guide/tutoriel de divers sujet", inline=False)
                        embed.add_field(name="Exemple 🧩", value="Scénarios d'exemple pour l'écriture de scénarios ou tester une fonctionnalité du bot.", inline=False)
                        embed.add_field(name="Divers 🎮", value="Jeux et scripts divers", inline=False)
                        embed.add_field(name="Utilisation", value="Cliquez sur la reaction correspondante à la catégorie que vous voulez affichez (inutilisable pendant une partie) ou utiliser la commande `" + prefixes[str(ctx.guild.id)][0] + "liste_scenarios nom_de_la_catégorie`.", inline=False)
                        message = await ctx.send(embed=embed)
                        for key in categories_scenarios.keys():
                            await message.add_reaction(key)
                        return
                except:
                    liste.remove("liste_scenarios.txt\n")
                    liste = ''.join(liste)
                    await ctx.send(f'```fix\n{liste}```')
                    
            else:
                liste = ''.join(liste)
                await ctx.send(f'```fix\n{liste}```')
        except:
            pass

def lire_variable(ctx, texte): #remplace v_variable_v par la valeur de variable
    texte = str(texte)
    for element in jeu[ctx.guild.id].variables.keys():
        texte = texte.replace('v_'+element+'_v',str(jeu[ctx.guild.id].variables[element]))
    return texte
    
async def envoyer_texte(ctx, texte, avec_reaction = "..."): #Convertit les liens images et sons dans le texte, ainsi que le formattage.
    """Envoyer le texte sur discord après avoir séparé les images et les sons"""
    with open('prefixes.json', 'r') as f: 
        prefixes = json.load(f)
        
    texte = lire_variable(ctx, texte)
    texte = texte.replace("[[PREFIX]]",prefixes[str(ctx.guild.id)][0])
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
            element = "```" + str(jeu[ctx.guild.id].markdown) + element + "```"
            message = await ctx.send(f'{element}')
    if "rafraichir" in jeu[ctx.guild.id].options:
        await message.add_reaction(jeu[ctx.guild.id].options["rafraichir"])
    if "inventaire" in jeu[ctx.guild.id].options:
        await message.add_reaction(jeu[ctx.guild.id].options["inventaire"])
    if avec_reaction == "ok":
        jeu[ctx.guild.id].last_reaction = element
        for case_verifiee in jeu[ctx.guild.id].case[jeu[ctx.guild.id].emplacement]:
            alias = ""
            if isinstance(case_verifiee,list) is False:
                case = str(case_verifiee)
            else:
                case = str(case_verifiee[0])
            
            if "->" in case:
                    alias = case.split("->")[0]
                    case = int(case.split("->")[1]) - 1
            else:
                    case = int(case) - 1
                    
            if alias in jeu[ctx.guild.id].alias_reaction:
                await message.add_reaction(jeu[ctx.guild.id].alias_reaction[alias])
            elif case not in (996,997,998) and jeu[ctx.guild.id].salle_react[case] != "...":
                await message.add_reaction(jeu[ctx.guild.id].salle_react[case])
        if len(jeu[ctx.guild.id].salle_reaction[str(jeu[ctx.guild.id].emplacement)]) > 0:
            emojis = jeu[ctx.guild.id].salle_reaction[str(jeu[ctx.guild.id].emplacement)]
            for emoji in emojis:
                await message.add_reaction(emoji)

async def verifier_objets(ctx): #Verifie les objets, variables et conditions présents dans une salle
    valeur = ""
    changement = 0
    if jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][0] != "|" :
        for o in range(jeu[ctx.guild.id].nb_objets[jeu[ctx.guild.id].emplacement]):
            if jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][1+(o*5)] == "invisible":
                jeu[ctx.guild.id].description[jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][0+(o*5)]] = jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][4+(o*5)]
                if jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][0+(o*5)][0] != "-" and jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][0+(o*5)] not in jeu[ctx.guild.id].inventaire_invisible:
                    jeu[ctx.guild.id].inventaire_invisible.append(jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][0+(o*5)])
                    changement = 1
                elif jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][0+(o*5)][0] == "-":
                    if jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][0+(o*5)][1:] in jeu[ctx.guild.id].inventaire_invisible:
                        jeu[ctx.guild.id].inventaire_invisible.remove(jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][0+(o*5)][1:])
                        changement = 1
                    elif jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][0+(o*5)][1:] in jeu[ctx.guild.id].inventaire_en_cours:
                        jeu[ctx.guild.id].inventaire_en_cours.remove(jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][0+(o*5)][1:])
                        changement = 1
            elif jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][1+(o*5)] == "variable":
                jeu[ctx.guild.id].variables_description[jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][0+(o*5)]] = lire_variable(ctx, jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][4+(o*5)])
                try:
                    if "%" in jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][2+(o*5)]:
                        valeur = lire_variable(ctx, jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][2+(o*5)][2:])
                        valeur = valeur.split(":")
                        valeur = jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][2+(o*5)][1] + str(random.randint(int(valeur[0]),int(valeur[1])))
                        jeu[ctx.guild.id].variables["resultat"] = valeur[1:]
                    else:
                        valeur = lire_variable(ctx, jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][2+(o*5)])
                    if "+" not in valeur and "-" not in valeur:
                        jeu[ctx.guild.id].variables[jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][0+(o*5)]] = int(valeur[1:])
                    else:
                        jeu[ctx.guild.id].variables[jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][0+(o*5)]] = jeu[ctx.guild.id].variables[jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][0+(o*5)]] + int(valeur)
                    changement = 1
                except:
                    await ctx.send(f'```fix\nErreur [001] dans la variable {jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][0+(o*5)]} et sa valeur ajoutée {lire_variable(ctx, jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][2+(o*5)])}```')
            if jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][1+(o*5)] == "invisible" or jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][1+(o*5)] == "variable":
                if jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][3+(o*5)] != "null" and changement == 1:
                    await envoyer_texte(ctx,jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][3+(o*5)])

async def condition_acces(ctx,case_actuelle,code="0"): #Vérifie si les conditions d'accès à une salle sont respectées
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
                if objet_test[1:] in jeu[ctx.guild.id].inventaire_en_cours or objet_test[1:] in jeu[ctx.guild.id].inventaire_invisible:
                    test = 2
                    break
                else:
                    test = 1
            elif "." in objet_test:   ### A partir de là, vérifier si c'est une variable.[operateur].valeur (donc si y'a un ".")
                try: #Au cas où la variable indiqué n'existe pas, dù à une erreur dans le scénario 
                    objet_test = objet_test.split(".") #objet_test[0] = valeur/variable, [1] = opérateur, [2] = valeur/variable
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
                        await ctx.send(f'```fix\n{objet_test} est incorrect```')
                        break
                except:
                    await ctx.send(f'```fix\nLe scénario comporte une syntaxe incorrecte : probablement une variable qui n\'existe pas.```')
                    test = 2
                    break
            else:
                if objet_test not in jeu[ctx.guild.id].inventaire_en_cours and objet_test not in jeu[ctx.guild.id].inventaire_invisible:
                    test = 2
                    break
                else:
                    test = 1
    return test
    
async def executer_event(ctx,code="0",case_verifiee=[]):
    try:
        temporaire = case_verifiee[3] #on garde de coté le texte de la case si y'a pas d'erreur
        jeu[ctx.guild.id].emplacement_precedent = jeu[ctx.guild.id].emplacement
        jeu[ctx.guild.id].emplacement = int(case_verifiee[2])-1
        if temporaire != "null": #pas d'erreur (except) ni de texte null, on envoit
            await envoyer_texte(ctx,temporaire,avec_reaction="ok")
        if jeu[ctx.guild.id].texte[jeu[ctx.guild.id].emplacement] != "null":
            await envoyer_texte(ctx,jeu[ctx.guild.id].texte[jeu[ctx.guild.id].emplacement])
        await verifier_objets(ctx)
        await verifier_cases_speciales(ctx,code)
        return "break"
    except ValueError:
        if case_verifiee[2] == "null":
            if case_verifiee[3] != "null":
                await envoyer_texte(ctx,case_verifiee[3])
        elif "&&" in case_verifiee[2]:
            try:
                objet_temp = case_verifiee[2].split("&&")
                jeu[ctx.guild.id].description[objet_temp[0]] = objet_temp[2]
                if objet_temp[1] == "inventaire":
                    if objet_temp[0][0] == "-" and objet_temp[0][1:] in jeu[ctx.guild.id].inventaire_en_cours:
                        jeu[ctx.guild.id].inventaire_en_cours.remove(objet_temp[0][1:])
                        if case_verifiee[3] != "null":
                             await envoyer_texte(ctx,case_verifiee[3])
                    elif objet_temp[0][0] != "-" and objet_temp[0] not in jeu[ctx.guild.id].inventaire_en_cours:
                        jeu[ctx.guild.id].inventaire_en_cours.append(objet_temp[0])
                        if case_verifiee[3] != "null":
                            await envoyer_texte(ctx,case_verifiee[3])
                    else:
                        pass  #s'il n'y a pas de changement, on ignore le 997, contrairement à !prendre qui affiche un texte
                elif objet_temp[1] == "invisible": 
                    if objet_temp[0][0] == "-" and objet_temp[0][1:] in jeu[ctx.guild.id].inventaire_invisible:
                        jeu[ctx.guild.id].inventaire_invisible.remove(objet_temp[0][1:])
                        if case_verifiee[3] != "null":
                            await envoyer_texte(ctx,case_verifiee[3])
                    elif objet_temp[0][0] != "-" and objet_temp[0] not in jeu[ctx.guild.id].inventaire_invisible:
                        jeu[ctx.guild.id].inventaire_invisible.append(objet_temp[0])
                        if case_verifiee[3] != "null":
                            await envoyer_texte(ctx,case_verifiee[3])
                    else:
                        pass  #s'il n'y a pas de changement, on ignore le 997, contrairement à !prendre qui affiche un texte
                elif objet_temp[1] == "variable": 
                    jeu[ctx.guild.id].variables[objet_temp[0]] = int(objet_temp[2])
                    jeu[ctx.guild.id].variables_description[objet_temp[0]] = str(objet_temp[3])
                    if case_verifiee[3] != "null":
                        await envoyer_texte(ctx,case_verifiee[3])
            except:
                pass
        else:
            try:
                valeur = ""
                variable_modifiee = case_verifiee[2].split(".")
                if not isinstance(variable_modifiee[2],int):
                    variable_modifiee[2] = lire_variable(ctx, variable_modifiee[2])
                if variable_modifiee[0] not in jeu[ctx.guild.id].variables:   
                    jeu[ctx.guild.id].variables[variable_modifiee[0]] = 0
                    jeu[ctx.guild.id].variables_description[variable_modifiee[0]] = "..."
                if "%" in variable_modifiee[2]:
                    valeur = variable_modifiee[2][1:].split(":")
                    valeur = variable_modifiee[1] + str(random.randint(int(valeur[0]),int(valeur[1])))
                    jeu[ctx.guild.id].variables["resultat"] = valeur[1:]
                else:
                    valeur = variable_modifiee[1] + variable_modifiee[2]
                if "+" not in valeur and "-" not in valeur:
                    jeu[ctx.guild.id].variables[variable_modifiee[0]] = int(valeur[1:])
                else:
                    jeu[ctx.guild.id].variables[variable_modifiee[0]] = jeu[ctx.guild.id].variables[variable_modifiee[0]] + int(valeur)
                if case_verifiee[3] != "null":
                    await envoyer_texte(ctx,case_verifiee[3])
            except:
                await ctx.send(f'```fix\nErreur [002] dans la variable {case_verifiee[0]} et sa valeur ajoutée {case_verifiee[2]}```')
    except IndexError: 
        await ctx.send(f'```fix\nLe scénario comporte une syntaxe incorrecte : probablement une erreur dans le nombre de salles.```')
        return "break"
    
async def verifier_cases_speciales(ctx,code="0"):
    for case_verifiee in jeu[ctx.guild.id].case[jeu[ctx.guild.id].emplacement]:
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
                    break
            else:
                pass
        elif case_verifiee[0] == "999" or case_verifiee[0] == "998":
            if case_verifiee[1] != "null":
                await envoyer_texte(ctx,case_verifiee[1])
            await asyncio.sleep(2)
            del jeu[ctx.guild.id]
            try: 
                voice = get(bot.voice_clients, guild=ctx.guild)
                if voice.is_playing():
                    voice.stop()
                await voice.disconnect()
            except:
                pass
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
    global base_url
    if ctx.guild.id in jeu:
        await ctx.send(f'```fix\nUne partie est déjà en cours```')
        return 0
    elif nom_scenario == "...":
        await ctx.send(f'```fix\nIl faut faire !jouer [nom_du_scenario], c\'est pas compliqué !```')
        return 0
    i = 0
    j = 2
    n = 0

    jeu[ctx.guild.id] = Rpg()
    # path = os.getcwd() + "\scenarios"; #pour test en local
    charger_url(ctx)
    
    try: # ouvre le scénario 
        
        if nom_scenario.lower().endswith(".txt") is False: 
            nom_scenario += ".txt"
        
        #à partir d'un dossier local
        # with open(os.path.join(path, nom_scenario), 'r', encoding="utf8") as data:
            # jeu[ctx.guild.id].scenario = data.readlines()
        
        # à partir d'une url  
        url_actuelle = ""
        for url in lien[ctx.guild.id].url_lien: #On vérifie si le scénario existe, url par url.
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
        jeu[ctx.guild.id].scenario = [x.replace("/n","\n") for x in data]
        
        
    except: # gérer l'erreur : le scénario n'a pas été trouvé sur une des url ou son nom est incorrect.
        await ctx.send(f'```fix\nLe scénario : "{nom_scenario}" n\'existe pas !```')
        del jeu[ctx.guild.id]
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
            
        jeu[ctx.guild.id].scenario = [ligne for ligne in jeu[ctx.guild.id].scenario if ligne != '\n']
        tableau_tmp = []
        tmp = ""
        
        for ligne in jeu[ctx.guild.id].scenario: #fusionne les lignes coupé par &&, et ignore les commentaires ("##")
            ligne = ligne.replace("\n","")
            ligne = ligne.split("##")[0]
            if ligne.endswith("&&"):
                tmp += ligne[:-2];
            else:
                if tmp != "":
                    tableau_tmp.append(tmp + ligne);
                    tmp = ""
                else:
                    tableau_tmp.append(ligne)
        jeu[ctx.guild.id].scenario = tableau_tmp    

        jeu[ctx.guild.id].scenario[0] = jeu[ctx.guild.id].scenario[0].replace('\n',"")
        if "|" in jeu[ctx.guild.id].scenario[0]:
            temp = jeu[ctx.guild.id].scenario[0].split("|")
            elem = 0
            for element in temp:
                if elem == 0:
                    jeu[ctx.guild.id].scenario[0] = element
                    elem += 1
                elif "§" in element:
                    element = element.split("§")
                    jeu[ctx.guild.id].options[element[0]] = element[1]
                    jeu[ctx.guild.id].options_inv[element[1]] = element[0]
        
        jeu[ctx.guild.id].scenario[3] = jeu[ctx.guild.id].scenario[3].rstrip().replace('+n+', '\n')
        num_markdown = jeu[ctx.guild.id].scenario[1].split(" ")
        if len(num_markdown) > 1:
            nombre_max = int(num_markdown[0])
            jeu[ctx.guild.id].markdown = str(num_markdown[1])+"\n"
        else:
            nombre_max = int(num_markdown[0])
            jeu[ctx.guild.id].markdown = "fix\n"
        await envoyer_texte(ctx, jeu[ctx.guild.id].scenario[0])
        while i < nombre_max:  #Pour chaque case du scénario
            jeu[ctx.guild.id].scenario[i+j] = jeu[ctx.guild.id].scenario[i+j].split(" ")
            jeu[ctx.guild.id].numero.append(jeu[ctx.guild.id].scenario[i+j][0])
            jeu[ctx.guild.id].salle_reaction[str(int(jeu[ctx.guild.id].numero[i])-1)] = ""
            if "§" in jeu[ctx.guild.id].scenario[i+j][1]: #Si on a ajouter une reaction au nom de salle (avec le séparateur §)
                jeu[ctx.guild.id].scenario[i+j][1] = jeu[ctx.guild.id].scenario[i+j][1].split("§") #on sépare nom et reaction
                jeu[ctx.guild.id].nom_salle.append(jeu[ctx.guild.id].scenario[i+j][1][0]) #on récupère le nom
                jeu[ctx.guild.id].salle_react.append(jeu[ctx.guild.id].scenario[i+j][1][1].replace('\n','')) #on récupère la réaction de salle
            else:
                jeu[ctx.guild.id].nom_salle.append(jeu[ctx.guild.id].scenario[i+j][1].replace('\n',''))
                jeu[ctx.guild.id].salle_react.append("...")
            j+=1
            jeu[ctx.guild.id].texte.append(jeu[ctx.guild.id].scenario[i+j])
            jeu[ctx.guild.id].texte[i] = jeu[ctx.guild.id].texte[i].rstrip().replace('+n+', '\n')
            j+=1
            if jeu[ctx.guild.id].scenario[i+j].strip() == "|":
                jeu[ctx.guild.id].objet.append(jeu[ctx.guild.id].scenario[i+j].strip())
                jeu[ctx.guild.id].nb_objets.append(0)
            else:   
                jeu[ctx.guild.id].objet.append(jeu[ctx.guild.id].scenario[i+j].strip().split("|"))
                jeu[ctx.guild.id].nb_objets.append(int(len(jeu[ctx.guild.id].objet[i])/5))
                for o in range(jeu[ctx.guild.id].nb_objets[i]):
                    jeu[ctx.guild.id].objet[i][0+(o*5)] = jeu[ctx.guild.id].objet[i][0+(o*5)].lower()  #On enlève les majuscule du nom
                    jeu[ctx.guild.id].objet_reaction[jeu[ctx.guild.id].objet[i][0+(o*5)]] = ""
                    if "§" in jeu[ctx.guild.id].objet[i][2+(o*5)]: #On regarde si reaction dans examiner meuble
                        jeu[ctx.guild.id].objet[i][2+(o*5)] = jeu[ctx.guild.id].objet[i][2+(o*5)].split("§")
                        jeu[ctx.guild.id].meubleex_react.append(jeu[ctx.guild.id].objet[i][2+(o*5)][1])
                        jeu[ctx.guild.id].objet_reaction[jeu[ctx.guild.id].objet[i][0+(o*5)]] = jeu[ctx.guild.id].objet_reaction[jeu[ctx.guild.id].objet[i][0+(o*5)]] + jeu[ctx.guild.id].objet[i][2+(o*5)][1]
                        jeu[ctx.guild.id].salle_reaction[str(int(jeu[ctx.guild.id].numero[i])-1)] = jeu[ctx.guild.id].salle_reaction[str(int(jeu[ctx.guild.id].numero[i])-1)] + jeu[ctx.guild.id].objet[i][2+(o*5)][1]
                        jeu[ctx.guild.id].objet[i][2+(o*5)] = jeu[ctx.guild.id].objet[i][2+(o*5)][0]
                    else:
                        jeu[ctx.guild.id].objet[i][2+(o*5)] = jeu[ctx.guild.id].objet[i][2+(o*5)].replace('+n+', '\n') #description meuble
                        
                    if "§" in jeu[ctx.guild.id].objet[i][3+(o*5)]: #On regarde si reaction dans prendre objet
                        jeu[ctx.guild.id].objet[i][3+(o*5)] = jeu[ctx.guild.id].objet[i][3+(o*5)].split("§")
                        jeu[ctx.guild.id].objetpr_react.append(jeu[ctx.guild.id].objet[i][3+(o*5)][1])
                        jeu[ctx.guild.id].objet_reaction[jeu[ctx.guild.id].objet[i][0+(o*5)]] = jeu[ctx.guild.id].objet_reaction[jeu[ctx.guild.id].objet[i][0+(o*5)]] + jeu[ctx.guild.id].objet[i][3+(o*5)][1]
                        jeu[ctx.guild.id].salle_reaction[str(int(jeu[ctx.guild.id].numero[i])-1)] = jeu[ctx.guild.id].salle_reaction[str(int(jeu[ctx.guild.id].numero[i])-1)] + jeu[ctx.guild.id].objet[i][3+(o*5)][1]
                        jeu[ctx.guild.id].objet[i][3+(o*5)] = jeu[ctx.guild.id].objet[i][3+(o*5)][0]
                    else:
                        jeu[ctx.guild.id].objet[i][3+(o*5)] = jeu[ctx.guild.id].objet[i][3+(o*5)].replace('+n+', '\n') #prendre objet
                        
                    if "§" in jeu[ctx.guild.id].objet[i][4+(o*5)]: #On regarde si reaction dans examiner objet
                        jeu[ctx.guild.id].objet[i][4+(o*5)] = jeu[ctx.guild.id].objet[i][4+(o*5)].split("§")
                        jeu[ctx.guild.id].objetex_react.append(jeu[ctx.guild.id].objet[i][4+(o*5)][1])
                        jeu[ctx.guild.id].objet_reaction[jeu[ctx.guild.id].objet[i][0+(o*5)]] = jeu[ctx.guild.id].objet_reaction[jeu[ctx.guild.id].objet[i][0+(o*5)]] + jeu[ctx.guild.id].objet[i][4+(o*5)][1]
                        jeu[ctx.guild.id].salle_reaction[str(int(jeu[ctx.guild.id].numero[i])-1)] = jeu[ctx.guild.id].salle_reaction[str(int(jeu[ctx.guild.id].numero[i])-1)] + jeu[ctx.guild.id].objet[i][4+(o*5)][1]
                        jeu[ctx.guild.id].objet[i][4+(o*5)] = jeu[ctx.guild.id].objet[i][4+(o*5)][0]
                    else:
                        jeu[ctx.guild.id].objet[i][4+(o*5)] = jeu[ctx.guild.id].objet[i][4+(o*5)].replace('+n+', '\n') #description objet

                    if jeu[ctx.guild.id].objet[i][1+(o*5)] == "variable":
                        jeu[ctx.guild.id].variables[jeu[ctx.guild.id].objet[i][0+(o*5)]] = 0
                        jeu[ctx.guild.id].variables_description[jeu[ctx.guild.id].objet[i][0+(o*5)]] = lire_variable(ctx, jeu[ctx.guild.id].objet[i][4+(o*5)])
                    else:
                        jeu[ctx.guild.id].description[jeu[ctx.guild.id].objet[i][0+(o*5)]] = jeu[ctx.guild.id].objet[i][4+(o*5)]
                        
                    jeu[ctx.guild.id].objet_reaction[jeu[ctx.guild.id].objet[i][0+(o*5)]] = tuple(jeu[ctx.guild.id].objet_reaction[jeu[ctx.guild.id].objet[i][0+(o*5)]])
            j+=1
            direction=[]
            while "*****" not in jeu[ctx.guild.id].scenario[i+j]:  #Pour chaque salle explorable à partir de l'emplacement.
                jeu[ctx.guild.id].scenario[i+j] = jeu[ctx.guild.id].scenario[i+j].split("|")
                if len(jeu[ctx.guild.id].scenario[i+j]) == 1:  #S'il n'y a qu'un numéro de salle
                    direction.append(jeu[ctx.guild.id].scenario[i+j][0]) #numéro de salle
                    j+=1
                elif jeu[ctx.guild.id].scenario[i+j][0] == "998" or jeu[ctx.guild.id].scenario[i+j][0] == "999":
                    end = []
                    end.append(jeu[ctx.guild.id].scenario[i+j][0]) 
                    jeu[ctx.guild.id].scenario[i+j][1] = jeu[ctx.guild.id].scenario[i+j][1].rstrip().replace('+n+', '\n')
                    end.append(jeu[ctx.guild.id].scenario[i+j][1])
                    direction.append(end)
                    j+=1
                else:
                    objet_requis = []
                    objet_requis.append(jeu[ctx.guild.id].scenario[i+j][0])  #numéro de salle
                    objet_requis.append(jeu[ctx.guild.id].scenario[i+j][1].split(" ")) #le(s) objet(s) requis   
                    emoji = []
                    emoji.append(0)
                    emoji.append([])
                    reaction_event = 0
                    for objet in objet_requis[1]:
                        if "§" in str(objet):
                            emoji[0] = int(objet.split("§")[0])
                            emoji[1].append(objet.split("§")[1])
                            jeu[ctx.guild.id].salle_reaction[str(int(jeu[ctx.guild.id].numero[i])-1)] = jeu[ctx.guild.id].salle_reaction[str(int(jeu[ctx.guild.id].numero[i])-1)] + objet.split("§")[1]
                            emoji.append(jeu[ctx.guild.id].scenario[i+j][2].rstrip().replace('+n+', '\n'))
                            emoji.append(jeu[ctx.guild.id].scenario[i+j][3].rstrip().replace('+n+', '\n'))
                            emoji.append(jeu[ctx.guild.id].scenario[i+j][4].rstrip().replace('+n+', '\n'))
                            reaction_event = 1
                        else:
                            emoji[1].append(objet)
                    if reaction_event == 1:
                        jeu[ctx.guild.id].event_react.append(emoji)
                    jeu[ctx.guild.id].scenario[i+j][2] = jeu[ctx.guild.id].scenario[i+j][2].rstrip().replace('+n+', '\n')
                    jeu[ctx.guild.id].scenario[i+j][3] = jeu[ctx.guild.id].scenario[i+j][3].rstrip().replace('+n+', '\n')
                    objet_requis.append(jeu[ctx.guild.id].scenario[i+j][2]) #texte si on a pas les objets ou evenement activé (997)
                    objet_requis.append(jeu[ctx.guild.id].scenario[i+j][3]) #texte si on a le(s) objet(s) requis ou si l'evenement s'active.
                    direction.append(objet_requis)
                    j+=1
            jeu[ctx.guild.id].case.append(direction)
            jeu[ctx.guild.id].salle_reaction[str(int(jeu[ctx.guild.id].numero[i])-1)] = list(jeu[ctx.guild.id].salle_reaction[str(int(jeu[ctx.guild.id].numero[i])-1)])
            i+=1
        case_actuelle = i+j
        if len(jeu[ctx.guild.id].scenario) > case_actuelle: #on vérifie si il y a des données après le scénarios
            alias_react = jeu[ctx.guild.id].scenario[i+j].split("|")
            for element in alias_react:
                element = element.split("§")
                jeu[ctx.guild.id].alias_reaction[element[0]] = element[1]
                jeu[ctx.guild.id].alias_reaction_inv[element[1]] = element[0]
        jeu[ctx.guild.id].nom_salle = [x.lower() for x in jeu[ctx.guild.id].nom_salle]       
        await envoyer_texte(ctx, jeu[ctx.guild.id].scenario[3],avec_reaction="ok")
        
        await verifier_objets(ctx) #regarder si il y a des objets/conditions invisibles ou des variables
        
        await verifier_cases_speciales(ctx) #vérifier si il y a des cases spéciales
        
        i = 0
                
    except:
            await ctx.send(f'```fix\nLe scénario : "{nom_scenario}" comporte une syntaxe incorrecte au chapitre {int(i)+1}```')
            del jeu[ctx.guild.id]
            try: 
                voice = get(bot.voice_clients, guild=ctx.guild)
                if voice.is_playing():
                    voice.stop()
                await voice.disconnect()
            except:
                pass

@bot.command(aliases=['av', 'move', 'go', 'do', 'action'])
@commands.guild_only()  
@in_channel('jdr-bot')
async def avancer(ctx,choix="...",code="0") : 
    """j!avancer X Y' avance dans la pièce X avec le code Y (si y'a un code)"""
    if ctx.guild.id not in jeu:
        await ctx.send(f'```fix\nAucune partie en cours !```')
        return
    if choix == "...":
        await ctx.send(f'```fix\nJe ne peux pas deviner où tu veux aller ... fait !avancer [numéro_ou_tu_vas] voyons !```')
        return
    if choix == "0":
        choix = str(jeu[ctx.guild.id].emplacement_precedent+1)
    choix = str(choix).lower()
    if choix in jeu[ctx.guild.id].nom_salle:
        choix = jeu[ctx.guild.id].nom_salle.index(choix)
        choix = str(int(choix)+1)
    
    try:
        test=0
        i = 0
        j = 0
        test_condition = 0
        case_testee = 0
        for case in jeu[ctx.guild.id].case[jeu[ctx.guild.id].emplacement]:
            if isinstance(case,list) is False and choix != "997":   # Si la case contient juste un chiffre (= numero de salle)
                if "->" in case:
                    if choix == case.split("->")[0]:
                        choix = case.split("->")[1]
                        test = 1
                        break
                elif choix == case:      #On vérifie si c'est le numéro de salle choisis
                    test = 1
                    break
            elif isinstance(case,list) and choix != "997":    #autre si choix = numero
                if "->" in case[0]:
                    if choix == case[0].split("->")[0]:
                        test = await condition_acces(ctx,case[1],code)
                        test_condition = 1
                        case_testee = i
                        if test == 1:
                            choix = case[0].split("->")[1]
                            break     
                else:
                    if choix == case[0]:
                        test = await condition_acces(ctx,case[1],code)
                        test_condition = 1
                        case_testee = i
                        if test == 1:
                            break
            i += 1
        if test == 2:
            if jeu[ctx.guild.id].case[jeu[ctx.guild.id].emplacement][case_testee][2] != "null":
                await envoyer_texte(ctx,jeu[ctx.guild.id].case[jeu[ctx.guild.id].emplacement][case_testee][2])
        if test == 1:
            if test_condition == 1:
                if jeu[ctx.guild.id].case[jeu[ctx.guild.id].emplacement][case_testee][3] != "null":
                    await envoyer_texte(ctx,jeu[ctx.guild.id].case[jeu[ctx.guild.id].emplacement][case_testee][3])
                if "$" in jeu[ctx.guild.id].case[jeu[ctx.guild.id].emplacement][case_testee][1]:
                        jeu[ctx.guild.id].case[jeu[ctx.guild.id].emplacement][case_testee] = jeu[ctx.guild.id].case[jeu[ctx.guild.id].emplacement][case_testee][0]
                        
            try:
                jeu[ctx.guild.id].variables["valeur"] = int(code)
                jeu[ctx.guild.id].emplacement_precedent = jeu[ctx.guild.id].emplacement
                jeu[ctx.guild.id].emplacement = int(choix)-1
                if jeu[ctx.guild.id].texte[jeu[ctx.guild.id].emplacement] != "null":
                    await envoyer_texte(ctx,jeu[ctx.guild.id].texte[jeu[ctx.guild.id].emplacement],avec_reaction="ok")
                
                await verifier_objets(ctx) #regarder si il y a des objets/conditions invisibles ou des variables
                
                await verifier_cases_speciales(ctx,code)
                
            except ValueError: 
                await ctx.send(f'```fix\nWarning : !Avancer [numéro] (valeur) : {code} n\'est pas une valeur numérique.```')
            
            
        elif test != 2:
            await ctx.send(f'```fix\nChoix impossible !```')
    except:
        await ctx.send(f'```fix\nChoix impossible ! (Une erreur est apparue)```')

@bot.command(aliases=['back', 'return'])
@commands.guild_only()  
@in_channel('jdr-bot')
async def reculer(ctx,code="0") :
    await avancer(ctx,str(jeu[ctx.guild.id].emplacement_precedent+1),code)

@bot.command(aliases=['pr', 'take'])
@commands.guild_only()
@in_channel('jdr-bot')
async def prendre(ctx,objet_cible="...",par_reponse=0) :
    """j!prendre X' prend l'objet X"""
    objet_cible = objet_cible.lower()
    i = 0
    try :
        for o in range(jeu[ctx.guild.id].nb_objets[jeu[ctx.guild.id].emplacement]):
            if objet_cible == jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][0+(o*5)]: #si cible = un des objets de la pièce, cible2 = "test1" (objet) et i = n° de l'objet
                i = o
                break
        if objet_cible == jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][0+(i*5)] and objet_cible != "null":
            if jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][1+(i*5)] == "invisible" or jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][1+(i*5)] == "variable":
                await ctx.send(f'```fix\nCe n\'est pas un objet à prendre```')
            elif jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][0+(i*5)] != "|" and jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][0+(i*5)] not in jeu[ctx.guild.id].inventaire_en_cours:
                jeu[ctx.guild.id].inventaire_en_cours.append(jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][0+(i*5)])
                jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][0+(i*5)] = "null"
                if jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][3+(i*5)] != "null":
                    await envoyer_texte(ctx,jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][3+(i*5)])
                if objet_cible in jeu[ctx.guild.id].objet_reaction.keys():
                    try:
                        for element in jeu[ctx.guild.id].objet_reaction[objet_cible]:
                            jeu[ctx.guild.id].salle_reaction[str(jeu[ctx.guild.id].emplacement)].remove(element)
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
        await ctx.send(f'```fix\nIl n\'y a pas de scénario en cours !```')
        

@bot.command(aliases=['ex', 'look','inspect','inspecter'])
@commands.guild_only()          
@in_channel('jdr-bot')
async def examiner(ctx,cible="ici") :
    """j!examiner [element]' examine l'élément (endroit de la pièce, objet de la pièece ou de l'inventaire, etc.). Par défaut : examine la pièce où on se trouve."""
    i = 0
    cible2 = ""
    cible = cible.lower()
    try:
        for o in range(jeu[ctx.guild.id].nb_objets[jeu[ctx.guild.id].emplacement]):
            if cible == jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][0+(o*5)]: #si cible = un des objets de la pièce, cible2 = "objet" et i = n° de l'objet
                cible2 = "objet"
                i = o
                break
            elif cible == jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][1+(o*5)] and jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][0+(o*5)] != "null" : #si cible = un des meubles de la pièce, cible2 = "meuble" et i = n° de l'objet
                cible2 = "meuble"
                i = o
                break

        if cible == "ici":
            await envoyer_texte(ctx, jeu[ctx.guild.id].texte[jeu[ctx.guild.id].emplacement],avec_reaction="ok") 
        elif cible == "invisible" or cible == "variable" or cible[0] == "-" or cible == "null":
            await ctx.send(f'```fix\nC\'est impossible !```')
        elif cible in jeu[ctx.guild.id].variables:
            if cible.endswith("_s") is False or cible == "resultat":
                await ctx.send(f'```fix\n{cible} : {jeu[ctx.guild.id].variables[cible]}```')
            await envoyer_texte(ctx,jeu[ctx.guild.id].variables_description[cible])
        elif cible in jeu[ctx.guild.id].inventaire_en_cours or cible in jeu[ctx.guild.id].inventaire_invisible or cible2 == "objet":
            await envoyer_texte(ctx,jeu[ctx.guild.id].description[cible])
        elif jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][0+(i*5)] != "|":
            if cible2 == "meuble" :
                if jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][0+(i*5)] not in jeu[ctx.guild.id].inventaire_en_cours:
                    await envoyer_texte(ctx,jeu[ctx.guild.id].objet[jeu[ctx.guild.id].emplacement][2+(i*5)])
                else:
                    await ctx.send(f'```fix\nIl n\'y a plus rien d\'intéressant ici pour l\'instant ...```')
            else: 
                await ctx.send(f'```fix\nJe ne comprend pas ce que vous voulez examiner.```')
        else:
            await ctx.send(f'```fix\nJe ne comprend pas ce que vous voulez examiner.```')
    except:
        await ctx.send(f'```fix\nIl n\'y a pas de scénario en cours !```')
        

@bot.command(aliases=['modif', 'edit', 'change','changer'])
@commands.guild_only()
@in_channel('jdr-bot')
async def modifier(ctx, variable="...", valeur=0):
    """Affiche l'inventaire du joueur"""
    try:
        if ctx.guild.id in jeu:
            if variable == "...":
                await ctx.send(f'```fix\nIl y a un souci dans vos arguments de commande. La commande est \'j!modifier nom_variable valeur\'```')
            elif variable in jeu[ctx.guild.id].variables:
                if variable.endswith("_m"):
                    jeu[ctx.guild.id].variables[variable] = int(valeur)
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
    if ctx.guild.id not in jeu: #patch
        await ctx.send(f'```fix\nAucune partie en cours !```')
        return
    if valeur == "...":
        await envoyer_texte(ctx,'Veuillez indiquer une réponse : "[[PREFIX]]reponse votre_reponse"')
    else:
        try:
            jeu[ctx.guild.id].variables["reponse"] = int(valeur)
            await verifier_cases_speciales(ctx,code="0")
        except:
            await prendre(ctx, str(valeur), 1)

        
@bot.command(aliases=['sc', 'loaded'])
@commands.guild_only()          
@in_channel('jdr-bot')
async def scenario_en_cours(ctx):
    """Affiche le scenario en cours"""
    try:
        await ctx.send(f'```fix\nLe scénario : \"{jeu[ctx.guild.id].scenario[0]}\" est en cours.```')
    except:
        await ctx.send(f'```fix\nIl n\'y a pas de scénario en cours !```')
        
@bot.command(aliases=['iv', 'item', 'items'])
@commands.guild_only()
@in_channel('jdr-bot')
async def inventaire(ctx):
    """Affiche l'inventaire du joueur"""
    if ctx.guild.id in jeu:
        embed=discord.Embed(color=0x17B93C ,title="**Inventaire**", description="Votre inventaire contient : ")
        for objet in jeu[ctx.guild.id].inventaire_en_cours:
            embed.add_field(name=objet, value=jeu[ctx.guild.id].description[objet], inline=False)
        message = await ctx.send(embed=embed)
        if "rafraichir" in jeu[ctx.guild.id].options:
            await message.add_reaction(jeu[ctx.guild.id].options["rafraichir"])
        if "inventaire" in jeu[ctx.guild.id].options:
            await message.add_reaction(jeu[ctx.guild.id].options["inventaire"])
    else:
        await ctx.send(f'```fix\nIl n\'y a pas de partie en cours !```')

@bot.command(aliases=['je', 'throw'])
@commands.guild_only()
@in_channel('jdr-bot')     
async def jeter(ctx,objet_jeter="???"):
    """jette un objet par terre"""
    if ctx.guild.id in jeu:
        if objet_jeter == "???":
            await ctx.send(f'```fix\nChoisissez un objet à jeter : !jeter [objet]```')
        elif objet_jeter in jeu[ctx.guild.id].inventaire_en_cours:
            jeu[ctx.guild.id].inventaire_en_cours.remove(objet_jeter)
            await ctx.send(f'```fix\nVous vous débarassez de \"{objet_jeter}\"```')
        else:
            await ctx.send(f'```fix\nVous n\'avez pas \"{objet_jeter}\" dans votre inventaire.```')
    else:
        await ctx.send(f'```fix\nIl n\'y a pas de partie en cours !```')


@bot.command(aliases=['ab', 'giveup'])
@commands.guild_only()
@in_channel('jdr-bot')
async def abandonner(ctx):
    """Met fin à la partie par un abandon"""
    if ctx.guild.id not in jeu:
        await ctx.send(f'```fix\nAucune partie en cours```')
        return
    await ctx.send(f'```fix\nVous abandonnez la partie ! C\'est lâche !!!```')
    del jeu[ctx.guild.id]
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
    # texte = texte.replace('+n','\n')
    # await ctx.send(f'```\n{texte}```')
    #inventaire_invisible_bis = ', '.join(map(str, jeu[ctx.guild.id].inventaire_invisible))
    #if ctx.guild.id in jeu:
    #    await ctx.send(f'```fix\n{jeu[ctx.guild.id].variables} ET {jeu[ctx.guild.id].variables_description}```')
    #else:
    #    await ctx.send(f'```fix\nIl n\'y a pas de partie en cours !```')

@bot.command(aliases=['info','information','infos','documentation', 'doc', 'fonctionnement','botinfo'])
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
    embed.add_field(name="**Ecrire un scénario**", value="Voir documentation", inline=True)
    embed.add_field(name="**Links**", value="[Github](https://github.com/Cyril-Fiesta/jdr-bot) | [Documentation](http://cyril-fiesta.fr/jdr-bot/Documentation-JDR-Bot.pdf) | [Invitation](https://discord.com/oauth2/authorize?client_id=521137132857982976&permissions=70671424&scope=bot) | [Discord officiel](https://discord.com/invite/Z63DtVV)", inline=False)
    embed.add_field(name="**Rejoignez-nous**", value="N'hésitez pas à nous rejoindre sur le discord [Make&Play](https://discord.com/invite/Z63DtVV), spécial Créateur en tout genre et Gamers ;)", inline=False)
    await ctx.send(embed=embed)

#bot.loop.create_task(list_servers())
bot.run(TOKEN)
