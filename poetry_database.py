"""
Famous Love Poetry Database
============================

Curated collection of public domain love poems from renowned writers.
All poems are pre-1928 (public domain in most jurisdictions).

Each poem includes:
- Title and author
- 6-8 lines suitable for cinematic slideshow
- Pre-defined visual metaphors for each line
"""

LOVE_POEMS = {
    "shakespeare": [
        {
            "title": "Sonnet 18",
            "author": "William Shakespeare",
            "year": "1609",
            "lines": [
                "Shall I compare thee to a summer's day?",
                "Thou art more lovely and more temperate.",
                "Rough winds do shake the darling buds of May,",
                "And summer's lease hath all too short a date.",
                "Sometime too hot the eye of heaven shines,",
                "And often is his gold complexion dimmed.",
                "But thy eternal summer shall not fade,",
                "Nor shall death brag thou wanderest in his shade."
            ],
            "visual_prompts": [
                "A golden summer meadow with wildflowers swaying in gentle breeze",
                "A serene garden bathed in soft morning light, perfectly balanced and harmonious",
                "Storm clouds gathering over a fragile rose garden in spring",
                "An hourglass with sand flowing, marking the passage of fleeting seasons",
                "Intense sunlight breaking through clouds, almost blinding in its brilliance",
                "The sun partially obscured by passing clouds, its golden rays softened",
                "An eternal sunset frozen in time, never fading into darkness",
                "A figure walking confidently through shadows, untouched by darkness"
            ]
        },
        {
            "title": "Sonnet 116",
            "author": "William Shakespeare",
            "year": "1609",
            "lines": [
                "Let me not to the marriage of true minds admit impediments.",
                "Love is not love which alters when it alteration finds,",
                "Or bends with the remover to remove.",
                "O no, it is an ever-fixed mark",
                "That looks on tempests and is never shaken.",
                "It is the star to every wandering bark,",
                "Love's not Time's fool, though rosy lips and cheeks",
                "Within his bending sickle's compass come."
            ],
            "visual_prompts": [
                "Two ancient trees with intertwined roots, standing unshaken through centuries",
                "A weathervane spinning in changing winds, while a mountain remains unmoved",
                "A lighthouse standing firm against crashing waves, refusing to bend",
                "A lighthouse beacon piercing through storm clouds, eternally fixed",
                "A ship tossed in violent seas, yet the lighthouse remains steady",
                "A guiding star shining above a lost ship on dark, turbulent waters",
                "An old clock tower with Time personified as a robed figure passing by",
                "A scythe resting against blooming roses, marking inevitable passage"
            ]
        }
    ],
    "rumi": [
        {
            "title": "The Minute I Heard My First Love Story",
            "author": "Rumi",
            "year": "13th Century",
            "lines": [
                "The minute I heard my first love story, I started looking for you,",
                "Not knowing how blind that was.",
                "Lovers don't finally meet somewhere,",
                "They're in each other all along.",
                "We are the mirror as well as the face in it.",
                "We are tasting the taste this minute of eternity.",
                "We are pain and what cures pain.",
                "We are the sweet cold water and the jar that pours."
            ],
            "visual_prompts": [
                "A person reading an ancient book by candlelight, eyes filled with wonder",
                "A figure wandering through fog, hands outstretched, searching blindly",
                "Two silhouettes walking toward each other from opposite horizons",
                "Two figures merging into one shadow, inseparable and eternal",
                "A ornate mirror reflecting a face, but the reflection is also looking back",
                "An hourglass where sand flows upward, defying time itself",
                "A wound healing with golden light emanating from within",
                "A crystal pitcher pouring water that transforms into light"
            ]
        },
        {
            "title": "Love Dogs",
            "author": "Rumi",
            "year": "13th Century",
            "lines": [
                "One night a man was crying, 'Allah! Allah!'",
                "His lips grew sweet with the praising,",
                "Until a cynic said, 'So! I have heard you calling out,",
                "But have you ever gotten any response?'",
                "The man had no answer to that.",
                "He quit praying and fell into a confused sleep.",
                "He dreamed he saw a wise man in a garden,",
                "'Why did you stop praising?' the sage asked."
            ],
            "visual_prompts": [
                "A lone figure kneeling under starlight, calling out to the heavens",
                "Honey dripping from lips, golden and sweet in moonlight",
                "A skeptical shadow figure standing in doorway, arms crossed",
                "An empty room echoing with unanswered prayers, silent and vast",
                "A person sitting in darkness, head in hands, questioning everything",
                "A figure lying in restless sleep, dreams swirling like smoke",
                "A lush mystical garden with an ancient sage sitting beneath a tree",
                "The sage's gentle eyes reflecting infinite wisdom and compassion"
            ]
        }
    ],
    "neruda": [
        {
            "title": "I Do Not Love You Except Because I Love You",
            "author": "Pablo Neruda",
            "year": "1924",
            "lines": [
                "I do not love you except because I love you.",
                "I go from loving to not loving you,",
                "From waiting to not waiting for you.",
                "My heart moves from cold to fire.",
                "I love you only because it's you the one I love.",
                "I hate you deeply, and hating you,",
                "Bend to you, and the measure of my changing love for you",
                "Is that I do not see you but love you blindly."
            ],
            "visual_prompts": [
                "A paradox visualized: two opposing forces creating perfect balance",
                "A pendulum swinging between two extremes, never resting",
                "A figure standing at a crossroads, torn between two paths",
                "A heart transforming from ice to flame, caught mid-transformation",
                "A single red thread connecting two distant souls across the void",
                "Two figures locked in an eternal dance of push and pull",
                "A measuring scale tipping wildly between extremes",
                "A blindfolded figure reaching out with absolute certainty"
            ]
        }
    ],
    "byron": [
        {
            "title": "She Walks in Beauty",
            "author": "Lord Byron",
            "year": "1814",
            "lines": [
                "She walks in beauty, like the night",
                "Of cloudless climes and starry skies,",
                "And all that's best of dark and bright",
                "Meet in her aspect and her eyes.",
                "Thus mellowed to that tender light",
                "Which heaven to gaudy day denies.",
                "One shade the more, one ray the less,",
                "Had half impaired the nameless grace."
            ],
            "visual_prompts": [
                "An elegant silhouette walking through moonlit gardens at midnight",
                "A clear night sky filled with countless stars, vast and infinite",
                "Light and shadow dancing together in perfect harmony",
                "A face illuminated by soft moonlight, eyes reflecting starlight",
                "Gentle twilight glow, neither harsh day nor complete darkness",
                "A serene night scene that surpasses the brightness of day",
                "A delicate balance on a knife's edge, perfection threatened",
                "An ethereal grace that cannot be named or captured"
            ]
        }
    ],
    "dickinson": [
        {
            "title": "Wild Nights",
            "author": "Emily Dickinson",
            "year": "1891",
            "lines": [
                "Wild nights! Wild nights!",
                "Were I with thee,",
                "Wild nights should be our luxury!",
                "Futile the winds to a heart in port,",
                "Done with the compass, done with the chart.",
                "Rowing in Eden! Ah! the sea!",
                "Might I but moor tonight in thee!"
            ],
            "visual_prompts": [
                "Storm-tossed seas under a turbulent sky, wild and untamed",
                "Two silhouettes standing together against the tempest",
                "A luxurious chamber with storm raging outside, safe within",
                "A ship safely anchored in a calm harbor, winds powerless",
                "Discarded navigation tools lying on a dock, no longer needed",
                "A small boat gliding through paradise waters, effortless and serene",
                "A ship seeking safe harbor as night falls, desperate for anchor"
            ]
        }
    ],
    "browning": [
        {
            "title": "How Do I Love Thee? (Sonnet 43)",
            "author": "Elizabeth Barrett Browning",
            "year": "1850",
            "lines": [
                "How do I love thee? Let me count the ways.",
                "I love thee to the depth and breadth and height",
                "My soul can reach, when feeling out of sight",
                "For the ends of being and ideal grace.",
                "I love thee to the level of every day's",
                "Most quiet need, by sun and candle-light.",
                "I love thee freely, as men strive for right.",
                "I love thee purely, as they turn from praise."
            ],
            "visual_prompts": [
                "A figure counting on fingers, each one glowing with light",
                "Infinite cosmic space stretching in all dimensions, boundless",
                "A soul reaching upward into the unknown, seeking transcendence",
                "The edge of existence where reality meets the divine",
                "Simple daily rituals: sunrise, candlelight, quiet moments",
                "Dawn breaking and candles burning, marking passage of ordinary days",
                "A figure breaking chains, choosing love without compulsion",
                "A humble figure turning away from applause, seeking only truth"
            ]
        }
    ],
    "keats": [
        {
            "title": "Bright Star",
            "author": "John Keats",
            "year": "1819",
            "lines": [
                "Bright star, would I were steadfast as thou art—",
                "Not in lone splendor hung aloft the night,",
                "And watching, with eternal lids apart,",
                "Like nature's patient, sleepless Eremite,",
                "The moving waters at their priestlike task",
                "Of pure ablution round earth's human shores,",
                "Or gazing on the new soft-fallen mask",
                "Of snow upon the mountains and the moors."
            ],
            "visual_prompts": [
                "A single brilliant star shining with unwavering constancy",
                "A solitary star in vast darkness, beautiful but isolated",
                "Eyes that never close, watching eternally without rest",
                "A hermit monk in meditation, patient and eternal",
                "Ocean waves performing their endless ritual cleansing",
                "Tides washing over shores in sacred, repetitive ceremony",
                "Fresh snow covering a mountain landscape like a veil",
                "Pristine white snow blanketing moorlands in peaceful silence"
            ]
        }
    ],
    "gibran": [
        {
            "title": "On Love (from The Prophet)",
            "author": "Kahlil Gibran",
            "year": "1923",
            "lines": [
                "When love beckons to you, follow him,",
                "Though his ways are hard and steep.",
                "And when his wings enfold you yield to him,",
                "Though the sword hidden among his pinions may wound you.",
                "And when he speaks to you believe in him,",
                "Though his voice may shatter your dreams as the north wind lays waste the garden.",
                "For even as love crowns you so shall he crucify you.",
                "Even as he is for your growth so is he for your pruning."
            ],
            "visual_prompts": [
                "A figure beckoning from a steep mountain path, calling upward",
                "A treacherous rocky path ascending into clouds, difficult but necessary",
                "Angelic wings embracing a figure, both protective and overwhelming",
                "A hidden blade among soft feathers, beauty concealing pain",
                "A voice emanating light, commanding belief and trust",
                "A violent wind destroying a beautiful garden, necessary destruction",
                "A crown of thorns transforming into a crown of gold",
                "A gardener pruning a tree, cutting away to encourage new growth"
            ]
        }
    ]
}

def get_random_poem(poet=None):
    """
    Get a random poem from the database.
    
    Args:
        poet: Optional poet name (shakespeare, rumi, neruda, etc.)
    
    Returns:
        dict: Poem with title, author, lines, and visual_prompts
    """
    import random
    
    if poet and poet.lower() in LOVE_POEMS:
        poems = LOVE_POEMS[poet.lower()]
    else:
        # Get all poems from all poets
        poems = []
        for poet_poems in LOVE_POEMS.values():
            poems.extend(poet_poems)
    
    return random.choice(poems)

def get_poem_by_title(title):
    """
    Get a specific poem by title.
    
    Args:
        title: Poem title (case-insensitive)
    
    Returns:
        dict: Poem or None if not found
    """
    title_lower = title.lower()
    for poet_poems in LOVE_POEMS.values():
        for poem in poet_poems:
            if poem["title"].lower() == title_lower:
                return poem
    return None

def list_available_poets():
    """Get list of available poets."""
    return list(LOVE_POEMS.keys())

def list_poems_by_poet(poet):
    """
    List all poems by a specific poet.
    
    Args:
        poet: Poet name
    
    Returns:
        list: List of poem titles
    """
    if poet.lower() in LOVE_POEMS:
        return [p["title"] for p in LOVE_POEMS[poet.lower()]]
    return []
