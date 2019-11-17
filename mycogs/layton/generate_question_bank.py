import yaml
import requests
from html.parser import HTMLParser
from bs4 import BeautifulSoup
from bs4.element import Tag

with open('data/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

class MyHTMLParser(HTMLParser):
    raw_data = None
    start_attrs = None
    def handle_starttag(self, tag, attrs):
        self.start_attrs = attrs
    def handle_data(self, x):
        if x.strip() != '':
            self.raw_data = x
parser = MyHTMLParser()

games = config['GAMES']

with open('data/puzzles.yaml', 'w') as out:
    print('', file=out)
with open('data/puzzles.yaml', 'a') as out:
    for game in games:
        puzzle_list_url = '{}/wiki/{}/List_of_puzzles'.format(
            config['URL'],
            game.replace(' ', '_')
        )
        resp = requests.get(puzzle_list_url)
        
        if resp.status_code != 200:
            raise Exception('Wiki page not found: ' + str(puzzle_list_url))
        
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        tables = soup.find_all('table', class_='wikitable')  # Story Puzzles and Extra Puzzles
        for table in tables:
            links = table.find_all('a')
            saved_links = []
            for l in links:
                try:
                    link = l['href']
                except KeyError:
                    continue
                if 'Puzzle:' in link and '(US)' not in link and link not in saved_links:
                    saved_links += link,
                    print(link + ':\n- ', file=out)
                    # puzzle_dict = {
                    #     'URL':config['URL'] + link,
                    #     'picarats': 30}

                    # puzzle_html = requests.get(puzzle_dict['URL'])
                    # puzzle_soup = BeautifulSoup(
                    #     puzzle_html.content, 'html.parser').find(
                    #         'div', class_='WikiaPageContentWrapper')
                    
                    # image = puzzle_soup.find('img', class_='pi-image-thumbnail')
                    # puzzle_dict['image'] = image['src']

                    # # Game
                    # parser.feed(str(puzzle_soup.select("div[data-source='game']")[0]))
                    # for attr in parser.start_attrs:
                    #     if attr[0] == 'title':
                    #         game = attr[1]
                    
                    # # Number
                    # parser.reset()
                    # parser.feed(str(puzzle_soup.select("div[data-source='number']")[0]))
                    # number = parser.raw_data

                    # # Picarats
                    # parser.reset()
                    # parser.feed(str(puzzle_soup.select("div[data-source='picarats']")[0]))
                    # picarats = parser.raw_data

                    # print(game, number, picarats)

                    # puzzle_dict['game'] = game
                    # puzzle_dict['number'] = number
                    # puzzle_dict['picarats'] = picarats
                    
                    # # Get Puzzle text
                    # puzzle_span = puzzle_soup.find('span', id='Puzzle').parent.parent
                    # puzzle_txts = []
                    # getting_text = None
                    # for txt_elem in puzzle_span.children:
                    #     try:
                    #         t = txt_elem.get_text()
                    #     except:
                    #         continue
                    #     if t == 'Hints':
                    #         break
                    #     if getting_text == 'text':
                    #         puzzle_txts += t,
                    #     if t == 'Puzzle':
                    #         getting_text = 'text'
                    
                    # # Get solutions
                    # puzzle_dict['puzzle'] = '\n'.join(puzzle_txts)
                    # correct = puzzle_span.find('span', id='Correct')
                    # end_table = correct.find_next('table')
                    # cur = correct
                    # sol_txts = []
                    # while 1:
                    #     if cur.find_next('table') != end_table:
                    #         break
                    #     p = cur.find_next('p')
                    #     sol_txts += p.get_text(),
                    #     cur = p
                    
                    # puzzle_dict['solution'] = '\n'.join(sol_txts)

                    # # Get solution image
                    # cur = correct
                    # sol_imgs = []
                    # while 1:
                    #     if cur.find_next('table') != end_table:
                    #         break
                    #     i = cur.find_next('img')
                    #     iurl = i['src']
                    #     if 'http' in iurl:
                    #         sol_imgs += iurl,
                    #     cur = i
                    
                    # puzzle_dict['solution_images'] = sol_imgs

                    # # Get hints
                    # hints = puzzle_span.find_all('div', class_='tabbertab')
                    # puzzle_dict['hints'] = [hint.get_text().strip() for hint in hints if 'Hint' in hint['title']]
                    
                    # print(puzzle_dict)
                    # quit()