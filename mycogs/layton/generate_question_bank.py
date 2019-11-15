import yaml
import requests
from bs4 import BeautifulSoup

with open('data/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

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
        print(resp.status_code)
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
                    # print(link, file=out)
                    puzzle_dict = {'URL': link}
                    puzzle_html = requests.get(config['URL'] + link)
                    puzzle_soup = BeautifulSoup(puzzle_html.content).find('div', class_='WikiaPageContentWrapper')
                    image = puzzle_soup.find('img', class_='pi-image-thumbnail')
                    puzzle_dict['imgURL'] = image['src']
                    puzzle_txt = puzzle_soup.find('span', id_='Puzzle')