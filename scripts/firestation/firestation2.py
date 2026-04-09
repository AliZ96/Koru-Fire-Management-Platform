import pandas as pd
import matplotlib.pyplot as plt

# Dosyayı oku
df = pd.read_csv("izmir_ground_accessibility_v1.csv")

# Sadece HIGH ve LOW filtrele
df_hl = df[df["risk_class"].isin(["HIGH", "LOW"])].copy()

print("Toplam (HIGH + LOW):", len(df_hl))
print("\nRisk dağılımı:")
print(df_hl["risk_class"].value_counts())


def random_points_by_class(high_count, low_count, show_plot=False, pause_seconds=3):
    """
    Manuel olarak verilen HIGH ve LOW sayısına göre rastgele noktaları seçer.
    İsterse matplotlib ile kısa süreli gösterir (Mac terminalinde takılmasın diye auto-close).

    Args:
        high_count (int): Seçilecek HIGH sayısı
        low_count (int): Seçilecek LOW sayısı
        show_plot (bool): True ise grafiği gösterir
        pause_seconds (int/float): Grafik açık kalma süresi (saniye)
    Returns:
        (high_sample_df, low_sample_df)
    """

    high_points = df_hl[df_hl["risk_class"] == "HIGH"]
    low_points = df_hl[df_hl["risk_class"] == "LOW"]

    if high_count > len(high_points):
        print(f"UYARI: Maksimum HIGH = {len(high_points)} (istek: {high_count}) -> max'a çekildi")
        high_count = len(high_points)

    if low_count > len(low_points):
        print(f"UYARI: Maksimum LOW = {len(low_points)} (istek: {low_count}) -> max'a çekildi")
        low_count = len(low_points)

    high_sample = high_points.sample(n=high_count)
    low_sample = low_points.sample(n=low_count)

    print("\nSeçilen Nokta Sayıları:")
    print("HIGH:", len(high_sample))
    print("LOW:", len(low_sample))

    if show_plot:
        plt.figure(figsize=(12, 8))

        if len(low_sample) > 0:
            plt.scatter(
                low_sample["center_lon"], low_sample["center_lat"],
                label=f"LOW ({len(low_sample)})",
                s=80, alpha=0.6, marker="s"
            )

        if len(high_sample) > 0:
            plt.scatter(
                high_sample["center_lon"], high_sample["center_lat"],
                label=f"HIGH ({len(high_sample)})",
                s=80, alpha=0.6, marker="o"
            )

        plt.xlabel("Longitude (center_lon)")
        plt.ylabel("Latitude (center_lat)")
        plt.title("İzmir - Rastgele HIGH & LOW Risk Noktaları")
        plt.legend()
        plt.grid(True, alpha=0.3)

        # Mac terminalinde takılmasın diye:
        plt.show(block=False)
        plt.pause(pause_seconds)
        plt.close()

    return high_sample, low_sample


# Örnek kullanım
x, y = random_points_by_class(high_count=100, low_count=0, show_plot=True, pause_seconds=3)
print(x.head())
high_array = x[["center_lon", "center_lat"]].to_numpy()
low_array  = y[["center_lon", "center_lat"]].to_numpy()

print(high_array[:])
print(low_array[:])