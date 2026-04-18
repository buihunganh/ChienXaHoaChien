# Chien Xa Hoa Chien

Bo khung du an game 2D theo phong cach ban tang theo luot (Python + Pygame).

## Yeu cau

- Python 3.11+
- pip

## Cai dat

```bash
pip install -r requirements.txt
```

## Chay game

```bash
python main.py
```

## Cau truc

- `assets/`: Tai nguyen game (anh, am thanh, font)
- `src/`: Ma nguon theo tung nhom chuc nang
- `tests/`: Bai test co ban

## Rules hien tai

- Di chuyen xe tang bang phim `A/D` hoac mui ten trai/phai, tieu hao nhien lieu theo quang duong.
- Dieu chinh goc nong sung bang phim `Mui ten len/xuong` (hoac `W/S`).
- Canh luc ban bang phim `Space`: nhan giu de thay doi luc, tha phim de ban.
- Moi luot se duoc cap mot loai dan ngau nhien (sat thuong va ban kinh no khac nhau).
- Gio thay doi theo luot va anh huong truc tiep den quy dao dan.
- Xe tang mat mau khi trong vung sat thuong vu no.
- Thang khi HP doi thu bang 0.

## Ghi chu

- Day la skeleton de phat trien nhanh.
- Ban co the bo sung map, vat can, vu khi va AI bot trong cac module hien co.
