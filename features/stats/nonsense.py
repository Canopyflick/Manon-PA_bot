import random


async def nonsense(update, context, first_name):
    demographics = ["listeners", f"people named {first_name}", "go-getters", "real humans", "people", "people", "chosen subjects", "things-with-a-hearbeat", "beings", "selected participants", "persons", "white young males", "mankind", "the populace", "the disenfranchized", "sapient specimen", "bipeds", "people-pleasers", "saviors", "heroes", "members", "Premium members", "earth dwellers", "narcissists", "cuties", "handsome motherfuckers", "Goal Gangsters", "good guys", "bad bitches", "OG VIP Hustlers", "readers", "lust objects"]
    demographic = random.choice(demographics)
    second_demographic = random.choice(demographics)
    percents = ["5%", "0.0069%", "7%", "83%", "20th percentile", "1%", "0.0420%", "19%", "6.2%", "0.12%", "half", "cohort"]
    percent = random.choice(percents)
    regions = [" globally", " worldwide", " in Wassenaar", " locally", " in the nation", ", hypothetically speaking", ", maybe!", " in the Netherlands", " (or maybe not)", " in Europe", " today", " this lunar year", " tomorrow", " (... for now, anyways)", " this side of the Atlantic", " in the observable universe"]
    region = random.choice(regions)
    adverbs = [" quite possibly ", " definitely ", " (it just so happens) ", ", presumably, ", ", without a doubt, ", ", so help us God, ", " (maybe) ", ", fugaciously, ", ", reconditely, ", " hitherto ", " (polyamorously) "]
    adverb = " "
    special_handcrafted_nonesense = ["You're in the top 1%!!!", "What a champ..!", "That's amazing!", "You could do better...", "You're in Enkhuizen!", "You're off-the-charts!", "You're well-positioned!", "You could do worse!", "You are unique!", "You are loved!", "You are on earth!", "You're alright.", "You're outperforming!", "You're better than France!", "You're semi-succesful!", "You're overachieving!"]
    if random.random() > 0.97:
        nonsense_message = random.choice(special_handcrafted_nonesense)
    else:
        if random.random() > 0.8:
            adverb = random.choice(adverbs)
        verbs = ["might be ", "have the potential to one day end up ", "will soon find yourself ", "are on course to being ", "deserve to be ", "should be ", "could've been ", "haven't been ", "stand a good chance of being ", "are exactly ", "are statistically unlikely to be ", f"are (much unlike other {second_demographic}) ", f"are, quite unlike other {second_demographic}, ", f"are (at least compared to other {second_demographic}) ", "are destined to be "]
        verb = "are"
        if random.random() > 0.8:
            verb = random.choice(verbs)
        top_or_bottom = "top"
        if random.random() > 0.8:
            top_or_bottom = "bottom"
        you_or_them = "You"
        if random.random() > 0.9:
            verb = ""     # Because many of these don't work with plural
            if random.random() > 0.6:
                you_or_them = "Your enemies are"
            else:
                you_or_them = "Your friends are"
        in_the = " in the "
        if random.random() > 0.94:
            if random.random() > 0.8:
                in_the = " better than the "
            else:
                in_the = " worse than the "
        closing_remark = ""
        if random.random() > 0.94:
            closing_remarks = ["Whoa...", "Just think of the implications!!", "That's insane!", "Not bad.", "... profit?!??", "Huh... Could be worse!", "Can you believe it?", "That's quite something.", "Be grateful for that.", "That's incredible.", "Big if True."]
            closing_remark = random.choice(closing_remarks)
        nonsense_messages = [f"{you_or_them}{adverb}{verb}{in_the}{top_or_bottom} {percent} of {demographic}{region}! {closing_remark}", "", "", "", "", ""]     # ~5 million unique options
        nonsense_message = nonsense_messages[0]
        # nonsense_message = random.choice(nonsense_messages)
    nonsense_message = nonsense_message.replace("  ", " ")
    return nonsense_message
