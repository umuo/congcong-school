import { Avatar } from './Avatar';
export interface LeagueRow { id:string;avatar_id:string;rank:number;name:string;xp:number;is_user:boolean }
export function LeagueStandings({rows}:{rows:LeagueRow[]}) {
  return <ol className="avatar-league">{rows.map(row=><li key={row.id} aria-label={`第 ${row.rank} 名，${row.name}，${row.xp} XP`}>
    <span className="avatar-league-rank">{row.rank}</span><Avatar id={row.avatar_id} size={36}/>
    <span className="avatar-league-name">{row.name}{row.is_user?'（我）':''}</span>
    <span className="avatar-league-xp">{row.xp} XP</span>
  </li>)}</ol>;
}
