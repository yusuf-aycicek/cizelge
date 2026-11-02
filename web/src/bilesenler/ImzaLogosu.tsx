import stil from "./ImzaLogosu.module.css";

/**
 * Geliştiricinin imza logosu (Yusuf Ayçiçek): yuvarlak köşeli bir kare içinde ">ya" ve yanıp
 * sönen bir imleç (komut satırı gibi). Yalnızca giriş sayfasındaki imzada kullanılır; ürünün
 * (Çizelge) logosu değildir, ürün logosu takvim ikonudur. Kare yazı renginde, yazı kart renginde: koyu temada renkler kendiliğinden yer
 * değiştirir. Süstür; yanındaki ürün adı okunur. Hareket azaltılmışsa imleç sabit durur.
 */
export function ImzaLogosu({ boyut = 32, className }: { boyut?: number; className?: string }) {
  return (
    <svg
      viewBox="0 0 100 100"
      width={boyut}
      height={boyut}
      className={[stil.logo, className].filter(Boolean).join(" ")}
      aria-hidden="true"
      focusable="false"
    >
      <rect x="6" y="6" width="88" height="88" rx="22" className={stil.kare} />
      <text x="20" y="60" className={stil.yazi}>
        &gt;ya
      </text>
      <rect x="70" y="41" width="11" height="22" className={stil.imlec} />
    </svg>
  );
}
