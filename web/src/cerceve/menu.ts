import {
  BookOpen,
  CalendarRange,
  ClipboardList,
  FileUp,
  GraduationCap,
  House,
  Layers,
  School,
  Settings,
  Share2,
  UserCog,
  type LucideIcon,
} from "lucide-react";

/** Menünün bölümleri; sayfa başlığının üstündeki küçük etiket de buradan gelir. */
export type MenuGrubu = "OKUL" | "DAĞITIM" | "PROGRAM";

export type MenuOgesi = { yol: string; ad: string; Ikon: LucideIcon; grup?: MenuGrubu };

/**
 * Menüdeki sayfalar, menüdeki sırayla. Ana sayfa en üstte ve Kullanıcılar en altta gruplanmaz;
 * aradakiler OKUL (okulun kendi verisi), DAĞITIM (kim hangi şubeye kaç saat) ve PROGRAM (üretim
 * ve yayın) başlıkları altındadır. Henüz yapılmamış olanlar "hazırlanıyor" sayfası gösterir.
 */
export const MENU: readonly MenuOgesi[] = [
  { yol: "/", ad: "Ana sayfa", Ikon: House },
  { yol: "/okul", ad: "Okul ayarları", Ikon: Settings, grup: "OKUL" },
  { yol: "/ogretmenler", ad: "Öğretmenler", Ikon: GraduationCap, grup: "OKUL" },
  { yol: "/siniflar", ad: "Sınıflar", Ikon: School, grup: "OKUL" },
  { yol: "/dersler", ad: "Dersler", Ikon: BookOpen, grup: "OKUL" },
  { yol: "/ice-aktarma", ad: "Excel'den aktar", Ikon: FileUp, grup: "OKUL" },
  { yol: "/seviye-sablonu", ad: "Seviye şablonu", Ikon: Layers, grup: "DAĞITIM" },
  { yol: "/ders-dagilimi", ad: "Ders dağılımı", Ikon: ClipboardList, grup: "DAĞITIM" },
  { yol: "/program", ad: "Program", Ikon: CalendarRange, grup: "PROGRAM" },
  { yol: "/yayin", ad: "Yayın ve paylaşım", Ikon: Share2, grup: "PROGRAM" },
  { yol: "/kullanicilar", ad: "Kullanıcılar", Ikon: UserCog },
];

/**
 * Bir adresin sayfa başlığı etiketi: menüdeki grubu (alt sayfalar da, ör. /ogretmenler/…
 * "OKUL"); grupsuz sayfalarda (Kullanıcılar, Hesabım) "HESAP"; bilinmeyen adreste yok.
 */
export function sayfaEtiketi(yol: string): string | undefined {
  if (yol === "/kullanicilar" || yol === "/hesabim") return "HESAP";
  const oge = MENU.find((m) => m.yol !== "/" && (yol === m.yol || yol.startsWith(m.yol + "/")));
  return oge?.grup;
}
