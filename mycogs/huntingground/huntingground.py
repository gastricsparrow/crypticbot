import json
import time
import random
import pathlib
import discord
import asyncio
from datetime import datetime
from typing import List
from redbot.core import commands, checks
from redbot.core.utils.chat_formatting import box, bold, humanize_list, underline
from redbot.core.utils.common_filters import normalize_smartquotes
from redbot.core.utils.predicates import MessagePredicate

HUNT_FILE = "magical_arcade_machine.json"
DATETIME_FORMAT = "%Y/%m/%d %H:%M:%S"
COMMANDS = ("**COMMANDS:**\n\n" +
        underline("?hunt:") + " View hunt status.\n" +
        underline("?hunt help:") + " Send this tutorial to your DM.\n" +
        underline("?hunt leaderboard:") + " View the leading teams and scores. Add 'time' after to see solve times.\n" +
        underline("?hunt join:") + " Join a team and start solving.\n" +
        underline("?hunt puzzles:") + " List available puzzles.\n" +
        underline("?hunt view <puzzle id>:") + " View a specific puzzle. *e.g. ?hunt view A1*\n" +
        underline("?hunt hint <puzzle id>:") + " View available hints for a puzzle. *e.g. ?hunt hint A1*\n" +
        underline("?hunt answer <puzzle id> <your answer>:") + " Submit an answer (case insensitive) to the puzzle. *e.g. ?hunt answer A1 MY ANSWER*\n")

class HuntingGround(commands.Cog):
    """UTS Puzzle Society's custom cog for puzzle hunting on Discord"""
    def __init__(self):
        super().__init__()
        self._load_hunt_data()
        self.start_time = datetime.strptime(self.hunt_info['Start time'], DATETIME_FORMAT)
        self.end_time = datetime.strptime(self.hunt_info['End time'], DATETIME_FORMAT)
        self._save_hunt_data()

    def _load_hunt_data(self) -> List[pathlib.Path]:
        path = pathlib.Path(__file__).parent.resolve() / ("data/" + HUNT_FILE)
        with path.open(encoding='utf-8') as f:
            hunt_data = json.load(f)
        self.hunt_info = hunt_data['Hunt info']
        self.team_info = hunt_data['Team info']
        self.participant_info = hunt_data['Participant info']
        self.puzzles = hunt_data['Puzzles']
        self.saving = False

    def _save_hunt_data(self) -> List[pathlib.Path]:
        path = pathlib.Path(__file__).parent.resolve() / ("data/" + HUNT_FILE)
        with path.open(encoding='utf-8', mode='w') as f:
            hunt_data = json.dump(self.format_hunt_data(), f, indent=2)
        self.saving = False

    async def wait_for_save(self):
        while self.saving:
            await asyncio.sleep(0.2)
        self.saving = True

    def format_hunt_data(self):
        return {
            'Hunt info': self.hunt_info,
            'Team info': self.team_info,
            'Participant info': self.participant_info,
            'Puzzles': self.puzzles
        }

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.check(lambda msg: msg.channel.category.name == 'Puzzle Hunt')
    async def hunt(self, ctx: commands.Context, *stuff):
        """
        UTS Puzzle Society's puzzle hunt bot.
        """
        if stuff:
            await ctx.send('Unrecognised command: ' + ' '.join(stuff))
        ending_time = datetime.strptime(self.hunt_info['End time'], DATETIME_FORMAT)
        await ctx.send("Current puzzle hunt: " + bold(self.hunt_info['Name']) +
        "\nTime left: " + bold(str(ending_time - datetime.now())) +
        "\n(Ends on " + self.hunt_info['End time'] + " AEDT)"
        "\n\n"
        + ("\"?hunt help\" to get more instructions. \"?hunt puzzles\" to view puzzles." if self.in_a_team(ctx.author)
            else "Use \"?hunt join\" to start or join a team. "
            "Or use \"?hunt help\" for a tutorial (sent to your DM)."))
        # .strftime("%d days, %H hours, %M minutes and %S seconds")

    @hunt.command(name="help")
    async def help(self, ctx):
        """
        Get an explanation of how the huntingground bot works.
        """
        await ctx.send("Instructions have been sent to your DM.")
        await ctx.author.send("Hello, I am PuzzleBot, and welcome to the " + bold(self.hunt_info['Name']) + " puzzle hunt"

        " by " + self.hunt_info['Author'] + '!'
        
        "\n\nTime left: " + bold(str(self.end_time - datetime.now())) +
        "\n(Ends on " + self.hunt_info['End time'] + " AEDT)"

        "\n\nYou can start by sending \"?hunt join\" to our Puzzle Discord server!\nAfter signing up, you'll have a brand new, awesome team channel to yourself!\n\n" +

        COMMANDS +

        "\nHere's a codesheet that might be useful: http://www.puzzledpint.com/files/2415/7835/9513/CodeSheet-201912.pdf\n"
        
        "\nRanking is based on points and solve time, so get in early!\n"
        "\nAre you ready? Return to the Puzzle Discord server and begin your solve!"
        )

    def get_instructions(self):
        return (COMMANDS +
            "*(To prevent guess spamming, you can only submit an answer to each puzzle once every minute.)*\n\n"

            "Here's a codesheet that might be useful: http://www.puzzledpint.com/files/2415/7835/9513/CodeSheet-201912.pdf\n\n"

            "**POINTS SYSTEM:**\nEach puzzle is worth a number of points, which you can check by viewing the puzzle list. Solving the preliminary puzzles will unlock more puzzles.\n"
            "Teams will be ranked based on points, and ties are broken by solve time - calculated as the duration between the start of the hunt and your last solve. So get in early!\n\n" +
            f"You can also @ {self.hunt_info['Tech support person']} for tech support, please do this sparingly.\n\n" +
            "```" + self.hunt_info['Introduction'] + '```\nAre you ready? Type \"?hunt puzzles\" to start!'
        )

    @hunt.command(name="join")
    async def join_team(self, ctx):
        author = ctx.author
        await ctx.send("Please check your DM.")
        if (str(author.id) in self.participant_info.keys()):
            your_team = self.team_info[self.participant_info[str(author.id)]["Team"]]['Name']
            message = f"You are already in a team: {bold(your_team)}\nCheck that your team channel is set up.\nTo change your team or get technical help, please @ mention our resident tech support {self.hunt_info['Tech support person']}."
            await author.send(message)
            return
        team_name = None
        message = ("Hi, welcome to the " + bold(self.hunt_info['Name']) + "!\n\n" + 
                "You can make a new team or join an existing one.\n" + 
                "If joining an existing team, make sure the spelling is precisely the same. We will ask the team leader for your access to the team channel.\n\n" + 
                "What's your team name?")
        while team_name is None:
            dm = await author.send(message)
            try:
                msg = await ctx.bot.wait_for(
                    "message", check=lambda msg: msg.author == author and msg.channel == dm.channel, timeout=60
                )
                team_name = msg.content.strip()
                if len(team_name) > 25 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789 ' for c in team_name.lower()):
                    message = "Team name must be 25 characters or fewer and can only contain alphanumeric characters and spaces!! Try again.\nWhat's your team name?"
                    team_name = None
                    continue
                else:
                    if any([team_name.lower() == team['Name'].lower() for team in self.team_info.values()]):
                        await author.send("This team exists. Do you want to request access to this team? yes/no")
                        yn_checker = MessagePredicate.yes_or_no(user=author)
                        try:
                            answer = await ctx.bot.wait_for(
                                "message", check=yn_checker, timeout=20)
                            if yn_checker.result:
                                # Yes
                                await author.send("You will be added to the team once the team leader accepts the request.")
                                # Request that access
                                team_channel_info = [team for team in self.team_info.values() if team_name.lower() == team['Name'].lower()][0]
                                team_leader = ctx.guild.get_member(int(team_channel_info['Members'][0]))
                                leader_dm = await team_leader.send("There's a request to join your team from " + author.display_name + ". Do you accept? yes/no")
                                try:
                                    leader_yn_checker = MessagePredicate.yes_or_no(user=team_leader, channel=leader_dm.channel)
                                    answer = await ctx.bot.wait_for(
                                        "message", check=leader_yn_checker, timeout=60)
                                    if leader_yn_checker.result:
                                        team_channel = ctx.bot.get_channel(int(team_channel_info['Channel']))
                                        await self.wait_for_save()
                                        await team_channel.set_permissions(author,read_messages=True)
                                        team_channel_info['Members'] += [str(author.id)]
                                        await team_channel.send(f"Welcome to team {bold(team_channel_info['Name'])}, <@{ctx.author.id}>!")
                                        # await team_channel.send(self.get_instructions())
                                        self.participant_info[str(author.id)] = {'Name': author.display_name, 'Team': str(team_channel_info['Channel'])}
                                        message = "You have been accepted."
                                        self._save_hunt_data()
                                        break
                                    else:
                                        message = "You were denied."
                                        break
                                except asyncio.TimeoutError:
                                    message = "I couldn't get an answer in time. Please try \"?hunt join\" again in the Puzzle Discord server."
                                    break
                            else:
                                # No
                                message = "Do you want to pick a different team name?"
                                try:
                                    answer = await ctx.bot.wait_for(
                                        "message", check=yn_checker, timeout=20)
                                    if yn_checker.result:
                                        message = "Enter a new team name."
                                        team_name = None
                                        continue
                                    else:
                                        await author.send("Ok. Goodbye.")
                                        break
                                except asyncio.TimeoutError:
                                    message = "I couldn't get your answer in time. Please try \"?hunt join\" again in the Puzzle Discord server."
                                    break
                        except asyncio.TimeoutError:
                            message = "I couldn't get your answer in time. Please try \"?hunt join\" again in the Puzzle Discord server."
                            break
                    else:
                        await self.wait_for_save()
                        permissions = {
                            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                            author: discord.PermissionOverwrite(read_messages=True),
                        }
                        team_channel = await ctx.guild.create_text_channel('team_' + team_name.lower().replace(' ', '_'), category=ctx.channel.category, overwrites=permissions)
                        await team_channel.send(f"Welcome to team {bold(team_name)}, <@{ctx.author.id}>!")
                        await team_channel.send(self.get_instructions())
                        self.team_info[str(team_channel.id)] = {
                            'Members': [str(author.id)],
                            'Name': team_name,
                            'Solved': [],
                            'Channel': team_channel.id,
                            'Solve time': datetime.strftime(datetime.now(), DATETIME_FORMAT),
                            'Attempts': {}
                        }
                        self.participant_info[str(author.id)] = {
                            'Team': str(team_channel.id),
                            'Name': author.display_name
                        }
                        self._save_hunt_data()
                        await ctx.send(bold(author.display_name) + " has created team " + bold(team_name) + "!")
                        message = "Team created successfully!"
            except asyncio.TimeoutError:
                message = "I couldn't get your answer in time. Please try \"?hunt join\" again in the Puzzle Discord server."
                break
        await author.send(message)

    def in_a_team(self, author):
        return str(author.id) in self.participant_info

    @hunt.command(name="puzzles")
    async def list_puzzles(self, ctx):
        # Check that this is a team channel
        author = ctx.author
        if not self.in_a_team(author):
            await ctx.send("You're not in a team just yet! Use \"?hunt join\".")
            return
        team = self.team_info[self.participant_info[str(author.id)]['Team']]
        await ctx.bot.get_channel(team['Channel']).send(self.create_puzzle_list(team['Solved']))

    def create_puzzle_list(self, solved_puzzle_ids):
        _s = '   '
        available = f"Here are your puzzles:\n```\nID{_s}Status{_s}Name{' ' * 18}Pts" + (f'{_s}Hints' if self.hunt_info['Hints unlocked'] > 0 else '')
        for puz_id in self.puzzles.keys():
            puzzle = self.puzzles[puz_id]
            solved = puz_id in solved_puzzle_ids
            if not puzzle['Prerequisite'] or all([puz in solved_puzzle_ids for puz in puzzle['Prerequisite']]):
                puzzle_line = f"{puz_id}{_s}{'SOLVED' if solved else '      '}{_s}{puzzle['Name']}"
                puzzle_line += " " * (36 - len(puzzle_line)) + str(puzzle['Points'])
                if self.hunt_info['Hints unlocked'] > 0:
                    puzzle_line += ' ' * (6 - len(str(puzzle['Points']))) + str(min(len(puzzle['Hints']), self.hunt_info['Hints unlocked']))
                available += "\n" + puzzle_line
            else:
                available += '\n' + puz_id + '   ' + 'LOCKED'
        available += '\n```\nView by: "?hunt view [puzzle id]"'
        return available

    @hunt.command(name="view")
    async def view_puzzle(self, ctx, puz_id):
        author = ctx.author
        if not self.in_a_team(author):
            await ctx.send("You're not in a team just yet! Use \"?hunt join\".")
            return
        team = self.team_info[self.participant_info[str(author.id)]['Team']]
        team_channel = ctx.guild.get_channel(int(team["Channel"]))
        if puz_id not in self.puzzles:
            await team_channel.send("Couldn't find puzzle. Please use the right Puzzle ID.\nFor example: ?hunt view A1")
            await team_channel.send(self.create_puzzle_list(team['Solved']))
            return
        puzzle = self.puzzles[puz_id]
        if not all([puz in team['Solved'] for puz in puzzle['Prerequisite']]):
            await team_channel.send(f"Puzzle is locked. Solve these prerequisite puzzles first:\n`{', '.join(puzzle['Prerequisite'])}`")
            return
        path = pathlib.Path(__file__).parent.resolve() / ("data/" + puzzle["Image"])
        await team_channel.send(f"**Puzzle {puz_id}: {puzzle['Name'].upper()}**\n\n{puzzle['Flavour text']}")
        await team_channel.send(file=discord.File(path))
        await team_channel.send(f"Reply \"?hunt answer {puz_id} <your answer>\" to attempt solving. e.g. ?hunt answer A1 MY ANSWER\n*Note: answers are case insensitive (aNsWeR == Answer)*\n")

    @hunt.command(name='answer')
    async def answer(self, ctx, puz_id, *attempt):
        author = ctx.author
        if not self.in_a_team(author):
            await ctx.send("You're not in a team just yet! Use \"?hunt join\".")
            return
        team = self.team_info[self.participant_info[str(author.id)]['Team']]
        team_channel = ctx.guild.get_channel(int(team["Channel"]))
        if puz_id not in self.puzzles:
            await team_channel.send("Couldn't find puzzle. Please use the right Puzzle ID.\nFor example: ?hunt answer A1 YOUR ANSWER")
            await team_channel.send(self.create_puzzle_list(team['Solved']))
            return
        if puz_id in self.team_info[self.participant_info[str(author.id)]['Team']]['Solved']:
            await team_channel.send("You have already solved this puzzle!")
            return
        attempt = ''.join([str(a).strip() for a in attempt])
        attempt = normalize_smartquotes(attempt).upper().replace(' ', '')
        if attempt == '':
            await team_channel.send("Invalid submission. Please submit a non-empty answer.")
            return
        if not attempt.isalpha():
            await team_channel.send("Invalid submission. Please submit answers with only alpha characters (A-Z).")
            return
        puzzle = self.puzzles[puz_id]
        answer = puzzle['Answer'].upper().replace(' ', '')
        
        if puz_id in team['Attempts'] and (datetime.now() - datetime.strptime(team['Attempts'][puz_id], DATETIME_FORMAT)).total_seconds() < 60:
            await team_channel.send("To prevent guess spamming, you can only submit an answer to each puzzle once every minute.")
            return
        self.wait_for_save()
        cur_time = datetime.strftime(datetime.now(), DATETIME_FORMAT)
        team['Attempts'][puz_id] = cur_time
        self._save_hunt_data()
        if attempt == answer:
            await team_channel.send(f"Correct! You have received {puzzle['Points']} point{'' if int(puzzle['Points']) == 1 else 's'}!")
            await self.wait_for_save()
            team['Solved'] += [puz_id]
            team['Solve time'] = cur_time
            self._save_hunt_data()
            if puzzle['Solved text']:
                await team_channel.send("```\n" + puzzle['Solved text'] + "\n```")
            if len(team['Solved']) >= len(self.puzzles):
                finished_teams = sum([1 for t, v in self.team_info.items() if len(v['Solved']) >= len(self.puzzles)])
                await self.announce(ctx, f"Congratulations to team {bold(team['Name'])} for finishing the hunt" + (" in :first_place: first place!" if finished_teams == 1 else " in :second_place: second place! " if finished_teams == 2 else " in :third_place: third place!" if finished_teams == 3 else "!"))
        else:
            await team_channel.send("Incorrect!")
            # await self.wait_for_save()
            # team_info = self.team_info[str(team['Channel'])]
            # if puz_id in team_info['Wrong guesses']:
            #     team_info['Wrong guesses'][puz_id] += 1
            # else:
            #     team_info['Wrong guesses'][puz_id] = 0
            # self._save_hunt_data()
            # if team_info['Wrong guesses'][puz_id] == self.hunt_info['Free guess limit']:
            #     await team_channel.send(f"{self.hunt_info['Free guess limit']} guesses reached. Time penalty will be added from the next attempt onward to prevent spam. (+ 1 minute per wrong answer)")
            # elif team_info['Wrong guesses'][puz_id] > self.hunt_info['Free guess limit']:
            #     await team_channel.send(f"(+ {self.hunt_info['Penalty per guess (min)']} minute)")

    @hunt.command(name='hint')
    async def view_hint(self, ctx, puz_id):
        author = ctx.author
        if not self.in_a_team(author):
            await ctx.send("You're not in a team just yet! Use \"?hunt join\".")
            return
        team = self.team_info[self.participant_info[str(author.id)]['Team']]
        team_channel = ctx.guild.get_channel(int(team["Channel"]))
        if puz_id not in self.puzzles:
            await team_channel.send("Couldn't find puzzle. Please use the right Puzzle ID.\nFor example: ?hunt hint A1")
            await team_channel.send(self.create_puzzle_list(team['Solved']))
            return
        puzzle = self.puzzles[puz_id]
        if not all([puz in team['Solved'] for puz in puzzle['Prerequisite']]):
            await team_channel.send(f"Puzzle is locked. Solve these prerequisite puzzles first:\n`{', '.join(puzzle['Prerequisite'])}`")
            return
        hints = puzzle['Hints'][:min(len(puzzle['Hints']), self.hunt_info['Hints unlocked'])]
        await team_channel.send(('**No available h' if self.hunt_info["Hints unlocked"] == 0 else '**H') + f'ints for puzzle {puz_id}**\n' + '\n'.join([str(i+1) + '. ' + hints[i] for i in range(len(hints))]))
    
    @hunt.command(name='leaderboard')
    async def show_leaderboard(self, ctx, time=None):
        leaderboard = sorted(
            [
                (
                    team['Name'],
                    sum([self.puzzles[puz_id]['Points'] for puz_id in team['Solved']]),
                    (datetime.strptime(team['Solve time'], DATETIME_FORMAT) - self.start_time).total_seconds() // 60
                    # (sum([max(0, wrong_guess - self.hunt_info['Free guess limit']) for wrong_guess in team['Wrong guesses'].values()]) if len(team["Wrong guesses"]) > 0 else 0) * self.hunt_info['Penalty per guess (min)']
                ) for team in self.team_info.values()
            ], key=lambda x: [x[1], -x[2]], reverse=True
        )
        await ctx.send(self.format_leaderboard(leaderboard, time == 'time'))

    def format_leaderboard(self, points, with_time):
        score_string = '```\n   Team' + ' ' * 28 + 'Score'
        if with_time:
            score_string += '   Time (min)'
            score_string += '\n' + '-' * 53 + '\n'
        else:
            score_string += '\n' + '-' * 43 + '\n'
        for idx, (team, score, time) in enumerate(points):
            team_score = str(idx + 1)
            team_score += ' ' * (3 - len(team_score))
            team_score += team
            team_score += ' ' * (35 - len(team_score))
            team_score += str(score)
            if with_time:
                team_score += ' ' * (43 - len(team_score))
                team_score += str(int(time))
            team_score += '\n'
            score_string += team_score
        score_string += '\n```'
        return score_string

    @hunt.command(name='remove')
    @checks.mod_or_permissions(administrator=True)
    async def exit_team(self, ctx, leaver_id):
        # Check if you're in a team
        author = ctx.guild.get_member(int(leaver_id))
        if not self.in_a_team(author):
            await ctx.send("The person's not in a team just yet! Use \"?hunt join\".")
            return
        team_channel_id = self.participant_info[str(author.id)]['Team']
        team_channel = ctx.guild.get_channel(int(team_channel_id))
        team_info = self.team_info[team_channel_id]
        dm = await author.send(f"You're about to leave team {team_info['Name']}.{' **As you are the last member, your team will be deleted along with your progress.**' if len(team_info['Members']) == 1 else ''}\n\nAre you sure? yes/no")
        yn_checker = MessagePredicate.yes_or_no(user=author, channel=dm.channel)
        try:
            answer = await ctx.bot.wait_for(
                "message", check=yn_checker, timeout=20)
            if yn_checker.result:
                # Yes
                await self.wait_for_save()
                del self.participant_info[str(author.id)]
                self.team_info[team_channel_id]['Members'].remove(str(author.id))
                if team_channel:
                    await team_channel.set_permissions(author,read_messages=False)
                # Check if you're the last member, if so # Delete team
                if len(self.team_info[team_channel_id]['Members']) == 0:
                    del self.team_info[team_channel_id]
                    if team_channel:
                        await team_channel.delete()
                    await author.send("Team has been deleted.")
                await author.send(f"You have left team {team_info['Name']}. Use \"?hunt join\" to join a team again.")
                self._save_hunt_data()
            else:
                await author.send('Ok! Nothing has been changed.')
        except asyncio.TimeoutError:
            await author.send("Your answer timed out. Nothing has been changed.")
        
    
    async def announce(self, ctx, announcement):
        for team in self.team_info:
            await ctx.guild.get_channel(int(team)).send("**ANNOUNCEMENT**\n" + announcement)
    
    @hunt.command(name='announce')
    @checks.mod_or_permissions(administrator=True)
    async def send_announcements(self, ctx, *announcement):
        announcement = ' '.join(announcement)
        await self.announce(ctx, announcement)

    @hunt.command(name='unlockhint')
    @checks.mod_or_permissions(administrator=True)
    async def unlock_hint(self, ctx, num):
        await self.wait_for_save()
        self.hunt_info['Hints unlocked'] = int(num)
        self._save_hunt_data()
        await ctx.author.send("The deed is done, milord.")

    @hunt.command(name='reload')
    @checks.mod_or_permissions(administrator=True)
    async def reload_hunt(self, ctx):
        self._load_hunt_data()
        await ctx.send("Hunt reloaded.")

    @hunt.command(name='adderrata')
    @checks.mod_or_permissions(administrator=True)
    async def add_errata(self, ctx, *errata):
        await self.wait_for_save()
        errata = ' '.join(errata)
        self.hunt_info['Errata'] += errata,
        self._save_hunt_data()
        await ctx.send("Hunt reloaded.")

    @hunt.command(name='errata')
    async def view_errata(self, ctx):
        await ctx.send("**List of Errata:**\n- " + '\n- '.join(self.hunt_info['Errata']))