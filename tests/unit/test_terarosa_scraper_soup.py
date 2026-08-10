"""Unit tests for the Terarosa scraper's product-page soup pruning.

The scraper sends ``str(soup)`` to the AI extractor, so
``TerarosaCoffeeScraper.preprocess_product_soup`` must narrow the detail page
(title, tasting tagline, price, weight/grind options, product photos) and drop
the header nav, purchase/shipping guide, review widgets and inline scripts
without losing the bean facts the extractor needs. The origin spec sheet is
delivered as product *photos* read via the screenshot, so the pruner must
retain the ``<img>`` elements.
"""

from bs4 import BeautifulSoup

from kissaten.scrapers.terarosa import TerarosaCoffeeScraper


def _make_scraper() -> TerarosaCoffeeScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return TerarosaCoffeeScraper(api_key="test-api-key")


def _terarosa_page() -> str:
    """Build a minimal page mirroring Terarosa's product_view_box layout."""

    def img(src: str) -> str:
        return (
            '<picture><source srcset="' + src + '.webp" type="image/webp">'
            '<img src="' + src + '.png"/></picture>'
        )

    gallery = (
        '<div class="product_view_img_wrap"><ul class="swiper-wrapper">'
        '<li>' + img("/UpImg/item/detail/0001") + '</li>'
        '<li>' + img("/UpImg/item/detail/0002") + '</li>'
        '</ul></div>'
    )
    core = (
        '<div class="cont">'
        '<h1 class="cont_title">에티오피아 예가체페 아리차 토착종 워시드</h1>'
        '<p class="cont_title_en">Ethiopia Yirgacheffe Aricha Heirloom Washed</p>'
        '<p class="tag">오렌지의 산뜻한 산미와 은은한 꽃내음</p>'
        '<p class="price">250g 29,500원, 1kg 93,000원</p>'
        '<select class="opt_weight"><option>옵션을 선택하세요</option>'
        '<option>250g</option><option>1kg</option></select>'
        '<select class="opt_grind"><option>옵션을 선택하세요</option>'
        '<option>갈지않음</option><option>중간 분쇄(드립용)</option></select>'
        '<input type="hidden" name="csrf" value="abc"/>'
        '<button type="submit">장바구니 담기</button>'
        '</div>'
    )
    boilerplate = (
        '<div class="product_view_cont_tab">상품정보 구매정보 후기(3)</div>'
        '<div class="product_view_cont"></div>'
        '<div class="product_view_cont_reivew">상품 구매 안내 결제 안내 '
        '배송비 3,000원... 전체후기 등록된 후기가 없습니다.</div>'
        '<div class="pagination">first prev 1 2 next last</div>'
    )
    header_nav = (
        '<div class="head_menu_wrap">로그인 회원가입 SHOP 쇼핑'
        ' SUBSCRIPTION 정기배송</div>'
    )
    recommended = (
        '<div class="search_list_box related_search"><div class="swiper-slide">'
        '<a href="/product/detail/?ItemCode=111">파나마 호세 게이샤 R 35000</a></div></div>'
    )
    footer = '<div class="foot">이용약관 개인정보처리방침 고객센터 (주)학산</div>'
    body = (
        '<div class="head_wrap">' + header_nav + '</div>'
        '<div class="cont_wrap product_view_wrap"><div class="product_view">'
        + '<div class="product_view_box">' + gallery + core + boilerplate + '</div>'
        + '</div></div>'
        + '<script>Kakao.init("x");</script>'
        + recommended
        + footer
    )
    return (
        '<html><head><title>t</title><style>body{}</style></head><body>'
        + body
        + '</body></html>'
    )


def test_preprocess_keeps_product_facts_and_drops_noise():
    scraper = _make_scraper()
    pruned = scraper.preprocess_product_soup(BeautifulSoup(_terarosa_page(), "lxml"))
    text = pruned.get_text(" ", strip=True)

    # Bean facts survive.
    assert "에티오피아 예가체페 아리차 토착종 워시드" in text
    assert "Ethiopia Yirgacheffe Aricha Heirloom Washed" in text
    assert "오렌지의 산뜻한 산미" in text
    assert "29,500원" in text and "93,000원" in text
    assert "250g" in text and "갈지않음" in text and "중간 분쇄(드립용)" in text

    # Boilerplate / chrome gone.
    assert "로그인 회원가입" not in text
    assert "상품 구매 안내" not in text
    assert "전체후기" not in text
    assert "상품정보 구매정보" not in text
    assert "Panama" not in text and "파나마 호세" not in text
    assert "이용약관" not in text

    # The origin-carrying product photos must survive (they are not text).
    imgs = pruned.find_all("img")
    assert len(imgs) == 2
    assert any(i.get("src") == "/UpImg/item/detail/0001.png" for i in imgs)


def test_preprocess_strips_markup_noise():
    scraper = _make_scraper()
    pruned = scraper.preprocess_product_soup(BeautifulSoup(_terarosa_page(), "lxml"))
    html = str(pruned)

    assert "<script" not in html and "<style" not in html
    assert "<input" not in html
    assert "swiper-wrapper" not in html       # classes stripped
    assert "product_view_box" not in html      # class stripped, text kept
    assert "csrf" not in html


def test_preprocess_falls_back_to_full_page_without_product_container():
    scraper = _make_scraper()
    html = "<html><body><p>not a product page</p></body></html>"
    soup = BeautifulSoup(html, "lxml")
    assert str(scraper.preprocess_product_soup(soup)) == str(soup)


def test_prune_on_live_shaped_page_retains_images_and_options():
    # Guard against regressing the image lift-out (lxml nests <img> in <source>).
    scraper = _make_scraper()
    page = (
        '<html><body><div class="product_view_box"><div class="cont">'
        '<p>제목 Title</p>'
        '<div class="product_view_img_wrap">'
        '<picture><source srcset="/a.webp"><img src="/a.png"/></picture>'
        '<picture><source srcset="/b.webp"><img src="/b.png"/></picture>'
        '</div></div></div></body></html>'
    )
    pruned = scraper.preprocess_product_soup(BeautifulSoup(page, "lxml"))
    imgs = pruned.find_all("img")
    assert sorted(i.get("src") for i in imgs) == ["/a.png", "/b.png"]
    text = pruned.get_text(" ", strip=True)
    assert "제목" in text and "Title" in text


def test_is_non_coffee_accessory_detects_junk_and_keeps_coffee():
    scraper = _make_scraper()
    cases = {
        "테라로사 쇼핑백": True,                        # shopping bag -> drop
        "Gift Packing": True,                        # bag english name -> drop
        "[테라로사 X 옥스포드] 강릉 본점 블록": True,      # collectible block -> drop
        "OXFORD Gangneung block": True,              # block english -> drop
        "테라로사 아이스크림 미니컵": True,              # ice cream -> drop
        # coffee products must survive
        "에티오피아 예가체페 아리차 토착종 워시드": False,
        "[8월 KING콩] 인도네시아 아체 리방가요 P88 워시드": False,
        "강릉 블렌드": False,
        "드립백 세트 (10개입)": False,
        "[Limited edition] 강릉 드립백 20개입&옥스포드 블록 세트": False,
        "Ethiopia Yirgacheffe Aricha Heirloom Washed": False,
        "에스프레소 블렌드": False,
        "": False,
        None: False,
    }
    for name, expected in cases.items():
        assert scraper._is_non_coffee_accessory(name) is expected, (name, expected)


def test_extract_product_urls_from_store_skips_accessories():
    import asyncio

    scraper = _make_scraper()
    grid = (
        '<html><body><ul id="itemList" class="productBox">'
        '<li><a data-key="100499" href="#"></a>'
        '<div class="cont_title text text_row2">에티오피아 예가체페 아리차 토착종 워시드</div>'
        '<div class="cont_title_en text text_row1">Ethiopia Yirgacheffe Aricha</div></li>'
        '<li><a data-key="100070" href="#"></a>'
        '<div class="cont_title text text_row2">테라로사 쇼핑백</div>'
        '<div class="cont_title_en text text_row1">Gift Packing</div></li>'
        '<li><a data-key="100363" href="#"></a>'
        '<div class="cont_title text text_row2">[테라로사 X 옥스포드] 강릉 본점 블록</div></li>'
        "</ul></body></html>"
    )
    async def fake_fetch(url, use_playwright=False):
        return BeautifulSoup(grid, "lxml")

    scraper.fetch_page = fake_fetch  # type: ignore[method-assign]
    urls = asyncio.run(
        scraper._extract_product_urls_from_store("https://example.com/list")
    )
    assert urls == ["https://www.terarosa.com/product/detail/?ItemCode=100499"]
