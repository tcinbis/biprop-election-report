import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

party_colors = {
    "PdA/Sol.": "#792a8f",
    "GPS": "#26b300",
    "SP": "#ea546f",
    "GLP": "#cbd401",
    "EVP": "#87bfdc",
    "BDP": "#ffff00",
    "CVP": "#f39f5e",
    "FDP": "#6268AF",
    "SVP": "#547d34",
    "EDU": "#3aa59a",
    "Lega": "#107a6d",
    "FGA": "#ff0000",
    "LPS": "#0000ff",
    "Others": "#00ff00",
}


def party_pie_plot(percentages, labels, legend):
    fig1, ax1 = plt.subplots()
    wedges = ax1.pie(
        percentages,
        labels=labels,
        # autopct="%1.1f%%",
        shadow=False,
        startangle=90,
    )

    for pie_wedge in wedges[0]:
        pie_wedge.set_edgecolor("white")

    ax1.legend(
        legend,
        title="Parties",
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1),
    )
    plt.show()


def plot_parliament(results_file, title):
    df = pd.read_csv(results_file, index_col=0)

    seats_wedges = []
    party_labels = []
    all_labels = []
    colors = []
    legend = []
    df.sort_index(inplace=True)
    for party in df.index:
        seats = df.loc[party].sum()
        seats_wedges.append(seats)
        if seats > 5:
            party_labels.append(party)
        else:
            party_labels.append("")
        all_labels.append(party)
        colors.append(party_colors.get(party))
        legend.append(f"{party} - {seats}")

    fig1, ax1 = plt.subplots()
    fig1.set_figwidth(8)

    wedges, texts = ax1.pie(
        seats_wedges,
        shadow=False,
        labels=party_labels,
        labeldistance=0.5,
        colors=colors,
        wedgeprops=dict(width=1),
        startangle=90,
    )

    for text in texts:
        text.set_color("white")
        text.set_fontweight("bold")
        text.set_horizontalalignment("center")

    fig1.legend(
        legend, title="Parties", loc="center left", bbox_to_anchor=(0, 0.5),
    )

    bbox_props = dict(boxstyle="square,pad=0.3", fc="w", ec="k", lw=0.72)
    kw = dict(
        arrowprops=dict(arrowstyle="-"), bbox=bbox_props, zorder=0, va="center"
    )

    for i, p in enumerate(wedges):
        ang = (p.theta2 - p.theta1) / 2.0 + p.theta1
        y = np.sin(np.deg2rad(ang))
        x = np.cos(np.deg2rad(ang))
        horizontal_alignment = {-1: "right", 1: "left", 0: "center"}[
            int(np.sign(x))
        ]
        connection_style = "angle,angleA=0,angleB={}".format(ang)
        kw["arrowprops"].update({"connectionstyle": connection_style})
        if party_labels[i] == "":
            y_offset = 0
            if all_labels[i] == "PdA/Sol.":
                y_offset = 0.36
            elif all_labels[i] == "EVP":
                y_offset = -0.1
            elif all_labels[i] == "CSP":
                y_offset = -0.15
            elif all_labels[i] == "Others":
                y_offset = 0.24
            elif all_labels[i] == "Lega":
                y_offset = 0.1
            elif all_labels[i] == "LPS":
                y_offset = -0.1

            ax1.annotate(
                all_labels[i],
                xy=(x, y),
                xytext=(1.4 * np.sign(x), 1.4 * y + y_offset),
                horizontalalignment=horizontal_alignment,
                **kw,
            )

    plt.tight_layout()
    plt.savefig(f"visdata/{title}")
    plt.show()


def main():
    original_file = "data/original-results.csv"
    others_file = "data/others-results.csv"
    biprop_file = "data/biprop-results.csv"
    nzz_file = "data/nzz-results.csv"
    # plot_parliament(biprop_file)
    # plot_parliament(original_file, "national_councile_original.png")
    plot_parliament(others_file, "national_council_with_others.png")
    # plot_parliament(nzz_file, "national_councile_nzz.png")


if __name__ == "__main__":
    main()
