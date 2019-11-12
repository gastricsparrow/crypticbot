import requests as req

"""
Grab Trivia Questions from OpenTDB API and populate yaml files for
redbot trivia.
"""

# CATEGORY_DICT = {
#     9: "generalknowledge", 10: "books", 11: "film", 12: "music", 13: "musicalsandtheatre", 14: "television", 15: "videogames", 16: "boardgames", 17: "scienceandnature", 18: "computerscience", 19: "mathematics", 20: "mythology", 21: "sports", 22: "geography", 23: "history", 24: "politics", 25: "art", 26: "celebrities", 27: "animals", 28: "vehicles", 29: "comics", 30: "gadgets", 31: "animeandmanga", 32: "cartoons"
# }

# TOKEN_REQUEST_URL = 'https://opentdb.com/api_token.php?command=request'

# res = req.get(TOKEN_REQUEST_URL)
# token_msg = res.json()

# if token_msg['response_code'] != 0:
#     print("Failed to get token. Full response:")
#     print(token_msg)
#     quit()

# token = token_msg['token']

# # for CATEGORY, CATEGORYNAME in CATEGORY_DICT.items():
CATEGORY = 9
CATEGORYNAME = 'generalknowledge'
# if 1:
#     done = False
#     all_questions = []
#     while not done:
#         print("Getting")
#         TRIVIA_REQUEST_URL = "https://opentdb.com/api.php?amount=50&category={}&token={}".format(CATEGORY, token)

#         res = req.get(TRIVIA_REQUEST_URL)
#         resdict = res.json()
#         if resdict['response_code'] != 0:
#             print(resdict)
#             done = True
#         else:
#             all_questions += resdict['results'],

# import pickle
# pickle.dump(all_questions, open(CATEGORYNAME + '_questions.pickle', 'wb'))

import pickle
questions = pickle.load(open('generalknowledge_questions.pickle', 'rb'))
import html
question_bank = open(CATEGORYNAME + '.yaml', 'a')
print('AUTHOR: ducducduc', file=question_bank)
for q in questions:
    if q['type'] != 'multiple':
        continue
    ques = html.unescape(q['question'])
    if '"' in ques:
        ques = ques.replace('"', '\\"')
        ques = f'"{ques}":'
    else:
        ques = ques + ':'
    print(ques, file=question_bank)
    answer = html.unescape(q['correct_answer'])
    print(f'- {answer}', file=question_bank)
question_bank.close()