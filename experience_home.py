"""Material-led homepage. All commercial destinations remain ordinary links."""


def render_home(link, image, media, wood_path):
    families = [
        ("01", "Packing & logistics", "Protection, built around your cargo.", "packing-plywood", "/products#packing", "Plywood · Cases · Pallets"),
        ("02", "Construction", "Panels for demanding work.", "film-faced-shuttering-plywood", "/products#construction", "Shuttering · Marine · Anti-skid"),
        ("03", "Interiors & joinery", "A better starting point for the finish.", "finger-joint-board", "/products#interiors", "Boards · Doors · Timber"),
    ]
    family_cards = "".join(
        f'<a class="cx-family" href="{link(href)}" data-reveal="image">'
        f'<div class="cx-family__image">{image(media["products"][slug])}</div>'
        f'<div class="cx-family__body"><span class="cx-index">{num} / {tags}</span>'
        f'<h3>{title}<span aria-hidden="true">↗</span></h3><p>{description}</p></div></a>'
        for num, title, description, slug, href, tags in families)
    application_cards = "".join(
        f'<a class="cx-application" href="{link(item["href"])}" data-reveal="image">'
        f'{image(item)}<div><span class="cx-index">0{i+1}</span><h3>{item["title"]}</h3>'
        f'<span class="cx-round-arrow" aria-hidden="true">↗</span></div></a>'
        for i, item in enumerate(media["applications"]))
    steps = [
        ("specify", "Start with the specification.", "Tell us the application, grade, dimensions and quantity. We’ll help resolve the details that affect performance and price."),
        ("make", "Agree the material and finish.", "Core, surface, tolerances and any special preparation are recorded in the order. The specification guides production."),
        ("check", "Define the checks that matter.", "Confirm the inspection points and documents for your order. Samples, moisture checks and packing details can be agreed before dispatch."),
        ("deliver", "Plan for the destination.", "Delivery terms, packing and dispatch documents are agreed around your route. For export, start with the destination port."),
    ]
    process_images = "".join(
        f'<figure class="cx-process__frame" data-process-image="{key}">{image(item)}'
        f'<figcaption>0{i+1} / {title.rstrip(".")} <span>Process illustration</span></figcaption></figure>'
        for i, ((key, title, _), item) in enumerate(zip(steps, media["process"])))
    process_steps = "".join(
        f'<div class="cx-process__step" data-process-step="{key}" data-reveal>'
        f'<span class="cx-index">0{i+1} / From enquiry to delivery</span><h3>{title}</h3><p>{description}</p>'
        f'<figure class="cx-process__mobile">{image(item)}<figcaption>Process illustration</figcaption></figure></div>'
        for i, ((key, title, description), item) in enumerate(zip(steps, media["process"])))
    hero = image(media["experience_hero"], eager=True, sizes="100vw").replace('<img ', '<img data-parallax ')
    wood = image(media["encyclopedia_hero"]).replace('<img ', '<img data-parallax ')
    return f'''
<section class="cx-hero" aria-labelledby="cx-hero-title">
  <div class="cx-hero__image">{hero}</div>
  <div class="cw-wrap cx-hero__content">
    <p class="cx-kicker"><span></span> Manufactured in Kerala. Made for your work.</p>
    <h1 id="cx-hero-title">Engineered wood.<br><em>Made to your spec.</em></h1>
    <p class="cx-hero__lead">Plywood, board and timber for construction, interiors and industrial packaging. Group manufacturing heritage since 1986.</p>
    <a class="cx-button cx-button--light" href="{link('/products')}">Explore the range <span aria-hidden="true">↗</span></a>
  </div>
  <div class="cw-wrap cx-hero__base"><a href="#materials">Discover Cochin Wood <span aria-hidden="true">↓</span></a><span>Perumbavoor, Kerala · India &amp; export</span><span class="cx-hero__credit">Warehouse illustration</span></div>
</section>
<section class="cx-intro cw-wrap" id="materials">
  <div data-reveal><p class="cx-kicker">Rooted in Kerala. Built on experience.</p><h2>Good work begins<br>with the <em>right material.</em></h2></div>
  <div class="cx-intro__detail" data-reveal><p>From the panel inside a finished room to the case protecting a shipment, the material has a job to do. We help you specify it.</p><a class="cx-text-link" href="{link('/about')}">Get to know Cochin Wood <span aria-hidden="true">↗</span></a><div class="cx-intro__facts"><span><b>1986</b>Our group’s manufacturing roots</span><span><b>16</b>Product lines to work with</span></div></div>
</section>
<section class="cx-materials cw-wrap" aria-labelledby="cx-materials-title">
  <div class="cx-section-heading" data-reveal><div><p class="cx-kicker">The collection</p><h2 id="cx-materials-title">A material for<br>what you’re making.</h2></div><a class="cx-text-link" href="{link('/products')}">View the full catalogue <span aria-hidden="true">↗</span></a></div>
  <div class="cx-families">{family_cards}</div>
</section>
<section class="cx-applications" aria-labelledby="cx-applications-title"><div class="cw-wrap">
  <div class="cx-section-heading" data-reveal><div><p class="cx-kicker">Across industries</p><h2 id="cx-applications-title">Materials at work.<br>Across industries.</h2></div><p>Strength for the structure. Finish for the interior. Protection for the journey. Start with what your work demands.</p></div>
  <div class="cx-applications__grid">{application_cards}</div>
  <div class="cx-section-foot"><span>Illustrations of typical applications</span><a class="cx-text-link" href="{link('/industries')}">Explore your industry <span aria-hidden="true">↗</span></a></div>
</div></section>
<section class="cx-process cw-wrap" aria-labelledby="cx-process-title">
  <div class="cx-section-heading" data-reveal><div><p class="cx-kicker">The details make the difference</p><h2 id="cx-process-title">Your specification.<br>Through every step.</h2></div><p>A clear brief becomes a clear order. Here is how we work through the material, checks and delivery with you.</p></div>
  <div class="cx-process__layout"><div class="cx-process__visual"><div class="cx-process__images">{process_images}</div></div><div class="cx-process__steps">{process_steps}</div></div>
  <a class="cx-text-link" href="{link('/plywood-factory')}">Explore the production process <span aria-hidden="true">↗</span></a>
</section>
<section class="cx-knowledge"><div class="cw-wrap cx-knowledge__layout">
  <div class="cx-knowledge__image" data-reveal="image">{wood}<span class="cx-knowledge__label">Grain. Density. Character.</span></div>
  <div class="cx-knowledge__copy" data-reveal><p class="cx-kicker">The Wood Encyclopedia</p><h2>Every wood<br>has a <em>character.</em></h2><p>Understand the grain, weight and working properties behind your material choices. Explore practical species notes and cited research.</p><a class="cx-button" href="{link(wood_path)}">Know your wood <span aria-hidden="true">↗</span></a></div>
</div></section>
<section class="cx-next"><div class="cw-wrap"><div data-reveal><p class="cx-kicker">Let’s put your plans into material</p><h2>Tell us what<br>you’re making.</h2></div><div class="cx-next__action" data-reveal><p>Share the application, quantity and destination. We’ll help with the next step.</p><a class="cx-button cx-button--light" href="{link('/contact#quote')}">Get a quote <span aria-hidden="true">↗</span></a><a class="cx-next__export" href="{link('/export')}">Planning an export order? Explore destinations ↗</a></div></div></section>
'''
