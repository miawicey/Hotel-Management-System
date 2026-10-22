"""The curated Nocturn Haven room-service catalogue.

Kept in one place so the seed command, the data migration, the portal and the
concierge context all describe the same menu.  All photography is hot-linked
from Unsplash's image CDN with an explicit crop/quality profile; every URL in
this file was verified to return HTTP 200.
"""

from decimal import Decimal

IMAGE_PARAMS = '?auto=format&fit=crop&w=900&q=80'


def _image(photo_id):
    return f'https://images.unsplash.com/{photo_id}{IMAGE_PARAMS}'


MENU_ITEMS = [
    # ---------------------------------------------------------- nasi goreng --
    {
        'name': 'Nasi Goreng Nocturn Signature',
        'description': (
            'Nasi goreng smoked beef, telur mata sapi, acar bawang merah, '
            'dan sambal matah khas Nocturn Haven.'
        ),
        'category': 'HEAVY_MEAL',
        'subcategory': 'NASI_GORENG',
        'price': Decimal('95000'),
        'image_url': _image('photo-1603133872878-684f208fb84b'),
        'is_recommended': True,
        'prep_minutes': 25,
        'sort_order': 10,
    },
    {
        'name': 'Nasi Goreng Kampung',
        'description': (
            'Resep kampung dengan ikan asin, terasi bakar, daun kemangi, '
            'dan telur ceplok.'
        ),
        'category': 'HEAVY_MEAL',
        'subcategory': 'NASI_GORENG',
        'price': Decimal('75000'),
        'image_url': _image('photo-1596797038530-2c107229654b'),
        'is_spicy': True,
        'prep_minutes': 20,
        'sort_order': 20,
    },
    {
        'name': 'Nasi Goreng Seafood',
        'description': (
            'Udang, cumi, dan scallop tumis butter bawang putih di atas '
            'nasi goreng gurih.'
        ),
        'category': 'HEAVY_MEAL',
        'subcategory': 'NASI_GORENG',
        'price': Decimal('115000'),
        'image_url': _image('photo-1512058564366-18510be2db19'),
        'prep_minutes': 25,
        'sort_order': 30,
    },
    {
        'name': 'Nasi Goreng Truffle & Porcini',
        'description': (
            'Nasi goreng creamy dengan minyak truffle, jamur porcini, '
            'dan taburan parmesan.'
        ),
        'category': 'HEAVY_MEAL',
        'subcategory': 'NASI_GORENG',
        'price': Decimal('145000'),
        'image_url': _image('photo-1633945274405-b6c8069047b0'),
        'is_recommended': True,
        'is_vegetarian': True,
        'prep_minutes': 25,
        'sort_order': 40,
    },
    # ------------------------------------------------------------------ sup --
    {
        'name': 'Sup Buntut Bakar',
        'description': (
            'Oxtail yang dibakar perlahan dalam kuah rempah bening, '
            'disajikan dengan kentang dan wortel.'
        ),
        'category': 'HEAVY_MEAL',
        'subcategory': 'SUP',
        'price': Decimal('125000'),
        'image_url': _image('photo-1547592166-23ac45744acd'),
        'prep_minutes': 35,
        'sort_order': 10,
    },
    {
        'name': 'Tom Yum Seafood',
        'description': (
            'Kuah asam pedas dengan udang, cumi, jamur jerami, serai, '
            'dan daun jeruk.'
        ),
        'category': 'HEAVY_MEAL',
        'subcategory': 'SUP',
        'price': Decimal('115000'),
        'image_url': _image('photo-1547592180-85f173990554'),
        'is_spicy': True,
        'prep_minutes': 25,
        'sort_order': 20,
    },
    {
        'name': 'Cream of Mushroom',
        'description': (
            'Sup jamur krim yang lembut dengan aroma thyme dan crouton '
            'mentega bawang putih.'
        ),
        'category': 'HEAVY_MEAL',
        'subcategory': 'SUP',
        'price': Decimal('85000'),
        'image_url': _image('photo-1603105037880-880cd4edfb0d'),
        'is_vegetarian': True,
        'prep_minutes': 20,
        'sort_order': 30,
    },
    # ------------------------------------------------------------------ mie --
    {
        'name': 'Mie Goreng Jawa',
        'description': (
            'Mie kuning goreng dengan ayam kampung, kol, dan kecap manis '
            'yang karamelisasi.'
        ),
        'category': 'HEAVY_MEAL',
        'subcategory': 'MIE',
        'price': Decimal('80000'),
        'image_url': _image('photo-1585032226651-759b368d7246'),
        'prep_minutes': 20,
        'sort_order': 10,
    },
    {
        'name': 'Ramen Shoyu',
        'description': (
            'Ramen dengan kaldu shoyu 12 jam, chashu ayam, telur ajitsuke, '
            'dan nori.'
        ),
        'category': 'HEAVY_MEAL',
        'subcategory': 'MIE',
        'price': Decimal('120000'),
        'image_url': _image('photo-1569718212165-3a8278d5f624'),
        'prep_minutes': 25,
        'sort_order': 20,
    },
    {
        'name': 'Mie Kuah Daging',
        'description': (
            'Mie lembut dalam kuah daging sapi berbumbu, irisan daging, '
            'bakso, dan sawi hijau.'
        ),
        'category': 'HEAVY_MEAL',
        'subcategory': 'MIE',
        'price': Decimal('95000'),
        'image_url': _image('photo-1552611052-33e04de081de'),
        'prep_minutes': 25,
        'sort_order': 30,
    },
    # -------------------------------------------------------- main courses --
    {
        'name': 'Wagyu Tenderloin Steak',
        'description': (
            '250 gram wagyu tenderloin, kentang truffle, asparagus, '
            'dan saus lada hitam.'
        ),
        'category': 'HEAVY_MEAL',
        'subcategory': 'MAIN_COURSE',
        'price': Decimal('385000'),
        'image_url': _image('photo-1546833999-b9f581a1996d'),
        'is_recommended': True,
        'prep_minutes': 35,
        'sort_order': 10,
    },
    {
        'name': 'Ayam Bakar Sambal Matah',
        'description': (
            'Ayam kampung bakar dengan sambal matah segar, nasi pandan, '
            'dan lalapan.'
        ),
        'category': 'HEAVY_MEAL',
        'subcategory': 'MAIN_COURSE',
        'price': Decimal('140000'),
        'image_url': _image('photo-1598103442097-8b74394b95c6'),
        'is_spicy': True,
        'prep_minutes': 30,
        'sort_order': 20,
    },
    {
        'name': 'Sate Ayam Madura',
        'description': (
            'Sepuluh tusuk sate ayam dengan bumbu kacang Madura, kecap, '
            'dan acar timun.'
        ),
        'category': 'HEAVY_MEAL',
        'subcategory': 'MAIN_COURSE',
        'price': Decimal('120000'),
        'image_url': _image('photo-1529042410759-befb1204b468'),
        'prep_minutes': 25,
        'sort_order': 30,
    },
    {
        'name': 'Nocturn Beef Burger',
        'description': (
            'Patty sapi 180 gram, cheddar aged, karamel bawang, selada, '
            'dan kentang goreng.'
        ),
        'category': 'HEAVY_MEAL',
        'subcategory': 'MAIN_COURSE',
        'price': Decimal('135000'),
        'image_url': _image('photo-1568901346375-23c9450c58cd'),
        'prep_minutes': 20,
        'sort_order': 40,
    },
    {
        'name': 'Grilled Salmon Teriyaki',
        'description': (
            'Salmon Norwegia panggang, glasir teriyaki, nasi jepang, '
            'dan bok choy.'
        ),
        'category': 'HEAVY_MEAL',
        'subcategory': 'MAIN_COURSE',
        'price': Decimal('265000'),
        'image_url': _image('photo-1467003909585-2f8a72700288'),
        'prep_minutes': 25,
        'sort_order': 50,
    },
    {
        'name': 'Truffle Mushroom Pasta',
        'description': (
            'Linguine dengan krim truffle, jamur campuran, parmesan, '
            'dan herba segar.'
        ),
        'category': 'HEAVY_MEAL',
        'subcategory': 'MAIN_COURSE',
        'price': Decimal('165000'),
        'image_url': _image('photo-1621996346565-e3dbc646d9a9'),
        'is_vegetarian': True,
        'prep_minutes': 25,
        'sort_order': 60,
    },
    {
        'name': 'Club Sandwich Nocturn',
        'description': (
            'Tiga lapis roti sourdough dengan ayam panggang, telur, '
            'bacon, tomat, dan kentang goreng.'
        ),
        'category': 'HEAVY_MEAL',
        'subcategory': 'MAIN_COURSE',
        'price': Decimal('95000'),
        'image_url': _image('photo-1528735602780-2552fd46c7af'),
        'prep_minutes': 15,
        'sort_order': 70,
    },
    # ----------------------------------------------------------- refreshers --
    {
        'name': 'Cucumber Mint Spritz',
        'description': (
            'Mentimun segar, daun mint, soda, dan sedikit lime. '
            'Pilihan paling ringan untuk siang hari.'
        ),
        'category': 'DRINK',
        'subcategory': 'REFRESHER',
        'price': Decimal('55000'),
        'image_url': _image('photo-1513558161293-cdaf765ed2fd'),
        'prep_minutes': 5,
        'sort_order': 10,
    },
    {
        'name': 'Sunset Passion Mocktail',
        'description': (
            'Markisa, jeruk, grenadine, dan soda dengan lapisan warna '
            'senja khas Nocturn Haven.'
        ),
        'category': 'DRINK',
        'subcategory': 'REFRESHER',
        'price': Decimal('60000'),
        'image_url': _image('photo-1621263764928-df1444c5e859'),
        'prep_minutes': 5,
        'sort_order': 20,
    },
    {
        'name': 'Lychee Rose Cooler',
        'description': (
            'Leci, air mawar, dan soda dingin dengan garnish kelopak mawar '
            'kering. Signature kami.'
        ),
        'category': 'DRINK',
        'subcategory': 'REFRESHER',
        'price': Decimal('65000'),
        'image_url': _image('photo-1544145945-f90425340c7e'),
        'is_recommended': True,
        'prep_minutes': 5,
        'sort_order': 30,
    },
    # ---------------------------------------------------------------- juices --
    {
        'name': 'Fresh Orange Juice',
        'description': 'Jeruk peras segar tanpa gula tambahan, disajikan dingin.',
        'category': 'DRINK',
        'subcategory': 'JUICE',
        'price': Decimal('45000'),
        'image_url': _image('photo-1600271886742-f049cd451bba'),
        'is_vegetarian': True,
        'prep_minutes': 5,
        'sort_order': 10,
    },
    {
        'name': 'Watermelon Juice',
        'description': 'Semangka manis yang diblender halus dengan sentuhan lime.',
        'category': 'DRINK',
        'subcategory': 'JUICE',
        'price': Decimal('45000'),
        'image_url': _image('photo-1589733955941-5eeaf752f6dd'),
        'is_vegetarian': True,
        'prep_minutes': 5,
        'sort_order': 20,
    },
    {
        'name': 'Tropical Mango Smoothie',
        'description': (
            'Mangga harum manis, yogurt Yunani, dan madu, diblender '
            'hingga lembut.'
        ),
        'category': 'DRINK',
        'subcategory': 'JUICE',
        'price': Decimal('60000'),
        'image_url': _image('photo-1622597467836-f3285f2131b8'),
        'is_vegetarian': True,
        'prep_minutes': 7,
        'sort_order': 30,
    },
    # ---------------------------------------------------------------- coffee --
    {
        'name': 'Nocturn Signature Latte',
        'description': (
            'Espresso house blend dengan susu segar dan sirup vanilla '
            'madu buatan sendiri.'
        ),
        'category': 'DRINK',
        'subcategory': 'COFFEE',
        'price': Decimal('50000'),
        'image_url': _image('photo-1461023058943-07fcbe16d735'),
        'prep_minutes': 7,
        'sort_order': 10,
    },
    {
        'name': 'Espresso',
        'description': 'Satu shot espresso pekat dari biji single-origin Gayo.',
        'category': 'DRINK',
        'subcategory': 'COFFEE',
        'price': Decimal('35000'),
        'image_url': _image('photo-1509042239860-f550ce710b93'),
        'prep_minutes': 5,
        'sort_order': 20,
    },
    {
        'name': 'Cappuccino',
        'description': 'Espresso dengan susu steamed dan foam tebal yang halus.',
        'category': 'DRINK',
        'subcategory': 'COFFEE',
        'price': Decimal('45000'),
        'image_url': _image('photo-1495474472287-4d71bcdd2085'),
        'prep_minutes': 6,
        'sort_order': 30,
    },
    # ------------------------------------------------------------------- tea --
    {
        'name': 'Earl Grey Royal',
        'description': 'Teh hitam bergamot dengan bunga jagung biru dan madu.',
        'category': 'DRINK',
        'subcategory': 'TEA',
        'price': Decimal('35000'),
        'image_url': _image('photo-1544787219-7f47ccb76574'),
        'is_vegetarian': True,
        'prep_minutes': 5,
        'sort_order': 10,
    },
    {
        'name': 'Jasmine Green Tea',
        'description': 'Teh hijau melati yang lembut, diseduh segar per cangkir.',
        'category': 'DRINK',
        'subcategory': 'TEA',
        'price': Decimal('35000'),
        'image_url': _image('photo-1576092768241-dec231879fc3'),
        'is_vegetarian': True,
        'prep_minutes': 5,
        'sort_order': 20,
    },
    {
        'name': 'Ginger Lemongrass Tea',
        'description': (
            'Jahe bakar dan serai segar dengan madu. Menenangkan '
            'setelah seharian.'
        ),
        'category': 'DRINK',
        'subcategory': 'TEA',
        'price': Decimal('40000'),
        'image_url': _image('photo-1597318181409-cf64d0b5d8a2'),
        'is_vegetarian': True,
        'prep_minutes': 5,
        'sort_order': 30,
    },
    # -------------------------------------------------------------- desserts --
    {
        'name': 'Midnight Chocolate Fondant',
        'description': (
            'Kue cokelat hangat dengan inti molten 70%, es krim vanila, '
            'dan berry compote.'
        ),
        'category': 'DESSERT',
        'subcategory': 'DESSERT',
        'price': Decimal('85000'),
        'image_url': _image('photo-1551024506-0bccd828d307'),
        'is_recommended': True,
        'is_vegetarian': True,
        'prep_minutes': 18,
        'sort_order': 10,
    },
    {
        'name': 'Vanilla Bean Panna Cotta',
        'description': (
            'Panna cotta vanila Madagaskar dengan saus markisa dan '
            'crumble almond.'
        ),
        'category': 'DESSERT',
        'subcategory': 'DESSERT',
        'price': Decimal('65000'),
        'image_url': _image('photo-1563805042-7684c019e1cb'),
        'is_vegetarian': True,
        'prep_minutes': 12,
        'sort_order': 20,
    },
    {
        'name': 'Classic New York Cheesecake',
        'description': 'Cheesecake creamy dengan crust graham dan coulis stroberi.',
        'category': 'DESSERT',
        'subcategory': 'DESSERT',
        'price': Decimal('75000'),
        'image_url': _image('photo-1578985545062-69928b1d9587'),
        'is_vegetarian': True,
        'prep_minutes': 12,
        'sort_order': 30,
    },
    {
        'name': 'Seasonal Fruit Platter',
        'description': 'Potongan buah tropis musiman dengan yogurt lime dan mint.',
        'category': 'DESSERT',
        'subcategory': 'DESSERT',
        'price': Decimal('55000'),
        'image_url': _image('photo-1490474418585-ba9bad8fd0ea'),
        'is_vegetarian': True,
        'prep_minutes': 10,
        'sort_order': 40,
    },
    {
        'name': 'Tropical Sorbet Trio',
        'description': 'Tiga scoop sorbet markisa, mangga, dan kelapa muda.',
        'category': 'DESSERT',
        'subcategory': 'DESSERT',
        'price': Decimal('60000'),
        'image_url': _image('photo-1567620905732-2d1ec7ab7445'),
        'is_vegetarian': True,
        'prep_minutes': 8,
        'sort_order': 50,
    },
]
