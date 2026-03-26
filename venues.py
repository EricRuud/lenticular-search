"""Venue data — bands confirmed to play specific local venues.

This validates that a band is at the right scale and actively booking
in the Bay Area scene.
"""

# Scraped from bottomofthehill.com/calendar.html on 2026-03-25
BOTTOM_OF_THE_HILL_2026 = {
    'Grrrl Gang', 'Street Eaters', 'Starry Eyed Cadet', 'Marbled Eye', 'Cemento',
    'Hannah Lew', 'Hot Goth GF', 'Louis XIV', 'Lazer Beam', 'The Schizophonics',
    'Sutros', 'Electric Machine Gun Tits', 'Sasquatch Borracho', 'Sex Mex',
    'Milk for the Angry', 'Hit Me Harold', 'Saintseneca', 'Gladie', 'Star 99',
    'WAAX', 'Starzdust', 'Cut-Rate Druggist', 'Merce Lemon', 'Fust', 'Georgia Maq',
    'Cece Coakley', 'Beatrix', 'Samantha Henson', 'LSD and the Search for God',
    'STOMACH BOOK', 'Girls Rituals', 'Teleco', 'Ian Santillano', 'Paper Straw',
    'Hollow Minds', 'Habibi', 'Mount Saint Elias', 'Ruby Ruby', 'Ephemerald',
    'Shy High', 'Slomosa', 'The Mainliners', 'Angela LaFlamme',
    'Homeboy Sandman', 'RDGLDGRN', 'The Jack Knives', 'The Stone Foxes',
    'Sam Chase', 'Swiss Cheese Airline', 'Ten Dollar Cash Reward', 'Boot Juice',
    'Cytrus', 'Michael Michael Motorcycle', 'Sgt. Splendor',
    'Young Fresh Fellows', 'The Rubinoos', 'Victor Krummenacher',
    'Rickshaw Billie\'s Burger Patrol', 'American Sharks', 'Evolfo', 'Hot Brother',
    'Grooblen', 'Sure Sure', 'Matt Jaffe', 'Indigo Elephant', 'El Ten Eleven',
    'Misandrist', 'The Toxhards', 'Boris & The Joy', 'Never Ending Fall',
    'Capital Soirée', 'Shayfer James', 'Katacombs', 'Everyone Asked About You',
    'First Day Back', 'Ashes To Amber', 'Nature TV', 'Preschool', 'Easy Honey',
    'Jack Shields', 'Sun Casino', 'FORAGER', 'Janaki',
    'Water From Your Eyes', 'Sour Widows', 'The Devil in California',
    'The Ghost Next Door', 'Bad Lemon', 'Electric Six', 'Anjimile',
    'Jared Benjamin', 'Diana', 'Useless Eaters', 'TINA!!!', 'Johnny',
    'Essenger', 'Echos', 'Bob Log III', 'Rock N Roll Adventure Kids',
    'Top Secret Robot Alliance', 'Shama Lama', 'The Strange Ones', 'Addalemon',
    'East Brothers', 'Foxtide', 'Hana Eid', 'Omnigone', 'Sloppy Seconds',
    'Memphis Murder Men', 'Middle Aged Queers', 'Accessory', 'Facing',
    'Supersuckers', 'Scott H. Biram', 'Hangtown', 'Chip Kinman', 'Steakhouse',
    'Temple Beautiful Band', 'Leanna Firestone', 'Abby Cates',
    'Half Rotten Goddess', 'Persephone', 'Rival Plague',
    'Foolish Relics', 'Sad Snack', 'For Horses', 'Outer Sunset',
    'Davia Schendel', 'Mikaela Davis', 'Jonathan Richman', 'Jeff Rosenstock',
    'Moon Walker', 'Pretoria', 'Super Cassette', 'Lip Critic', 'Flatwounds',
    'Bejalvin', 'The Dwarves', 'The Pandoras', 'Screaming Bloody Marys',
    'The Autocollants', 'Messer Chups', 'TsuShiMaMiRe',
    'Every Move A Picture', 'Applesaucer', 'Fake Your Own Death',
    'Igor & the Red Elvises', 'The Dead Sailor Girls', 'Christian Mistress',
    'The Lord Weird Slough Feg', 'Funeral Chant', 'Benny La Mar',
    'Mike Watt', 'Sister Double Happiness', 'Mayya',
    'Ted Leo and the Pharmacists', 'Rip Room', 'Pork Belly', 'Local Bylaws',
    'The Good Luck Thrift Store Outfit', 'Honey Run',
    'Widowspeak', 'Dead Gowns', 'MC Chris', 'Mega Ran',
    'Unsane', 'CNTS', 'Facet', 'Armand Hammer',
}


def is_venue_confirmed(artist):
    """Check if an artist has played Bottom of the Hill."""
    artist_lower = artist.lower()
    return any(artist_lower == b.lower() or artist_lower in b.lower()
               for b in BOTTOM_OF_THE_HILL_2026)
