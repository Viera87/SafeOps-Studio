import SafeOpsConsole from "@/components/SafeOpsConsole";
import { fetchScripts } from "@/lib/api";

export default async function Home() {
  const scripts = await fetchScripts();
  return <SafeOpsConsole scripts={scripts} />;
}
