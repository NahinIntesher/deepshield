'use client';
import {useUser} from '@/lib/UserContext';
import MemberDashboard from '@/components/MemberDashboard';
import LandingPage from '@/components/LandingPage';
export default function Home(){const {user}=useUser();return user?<MemberDashboard/>:<LandingPage/>}
