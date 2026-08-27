import type { Metadata } from "next";
import { RankingsClient } from "./_components/rankings-client";

export const metadata: Metadata = {
  title: "ランキング",
  description: "大会成績から算出したチームの競技ランキング。Tier・RP・優勝数で実力を可視化。",
};

export default function RankingsPage() {
  return <RankingsClient />;
}
