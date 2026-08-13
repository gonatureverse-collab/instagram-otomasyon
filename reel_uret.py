def son_gorsel_klasoru():
    klasorler = sorted(
        [x for x in GORSEL_KLASOR.glob("*") if x.is_dir()],
        key=lambda x: x.name
    )

    if not klasorler:
        raise FileNotFoundError(
            "gorseller/ klasöründe görsel klasörü bulunamadı."
        )

    return klasorler[-1]
